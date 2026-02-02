from __future__ import annotations

import csv
import io
from werkzeug.datastructures import FileStorage
from datetime import datetime
from urllib.parse import urlparse

from repositories.upload_repository import UploadRepository

from models import Upload

class UploadService:
    '''--- Write Operations ---'''
    @staticmethod
    def process_log_file(file_storage: FileStorage, user_id: str) -> Upload:
        '''Processes a log file and creates a new upload record.'''
        upload = UploadRepository.create_upload(user_id, file_storage.filename)

        try:
            # parse the file, assuming zscaler csv format
            raw_csv_text = file_storage.stream.read().decode('utf-8', errors='replace')
            UploadRepository.set_raw_csv_text(upload.id, raw_csv_text)
            stream = io.StringIO(raw_csv_text, newline=None)
            reader = csv.DictReader(stream)

            UploadService._validate_headers(reader.fieldnames)

            parsed_logs = []
            for row in reader:
                is_anomaly, reason, confidence_score = UploadService.parse_log_row(row)

                parsed_logs.append({
                    'upload_id': upload.id,
                    'timestamp': UploadService._parse_timestamp(row.get('datetime')),
                    'client_ip': row.get('clientip'),
                    'url': row.get('url'),
                    'action': row.get('action'),
                    'bytes_sent': int(row.get('sentbytes', 0)),
                    'risk_score': int(row.get('app_risk_score', 0)),
                    'is_anomaly': is_anomaly,
                    'anomaly_note': reason,
                    'confidence_score': confidence_score,
                })

            UploadRepository.add_logs_bulk(parsed_logs)
            UploadRepository.update_upload_status(upload.id, 'Completed')
            return upload
        except Exception as e:
            UploadRepository.update_upload_status(upload.id, 'Failed')
            raise
    
    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        '''Parses a timestamp string into a datetime object.'''
        try:
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')

    @staticmethod
    def _validate_headers(headers: list[str] | None) -> None:
        '''Validates the headers of a CSV file.'''
        required = {'datetime', 'clientip', 'url', 'action', 'sentbytes', 'app_risk_score'}
        present = set(headers or [])
        missing = sorted(required - present)
        if missing:
            raise ValueError(f"Missing required CSV headers: {missing}")
            
    '''--- Read Operations ---'''
    @staticmethod
    def parse_log_row(row: dict) -> tuple[bool, str, float]:
        reasons: list[str] = []

        risk = int(row.get('app_risk_score', 0) or 0)
        sent = int(row.get('sentbytes', 0) or 0)

        # scale risk starting from 4 and upt to 7
        if risk >= 4:
            risk_sev = min(1.0, (risk - 4) / 3) 
            reasons.append(f"High risk app (risk={risk})")
        else:
            risk_sev = 0.0

        # treat 5MB as threshold, 25MB+ as "max severe"
        if sent > 5_000_000:
            bytes_sev = min(1.0, (sent - 5_000_000) / 20_000_000)  
            reasons.append(f"Large data outbound ({sent} bytes)")
        else:
            bytes_sev = 0.0

        # keep the combined score in the range of 0-1
        confidence = 0.55 * risk_sev + 0.45 * bytes_sev

        if reasons:
            confidence = max(confidence, 0.25)
        confidence = min(1.0, confidence)

        return len(reasons) > 0, ", ".join(reasons), confidence

    @staticmethod
    def get_upload_summary(upload_id: str, bucket_minutes: int = 5) -> dict:
        if not isinstance(bucket_minutes, int) or bucket_minutes <= 0:
            bucket_minutes = 5

        logs = UploadRepository.get_all_logs_by_upload_id(upload_id)

        top_max = 10
        timeline_buckets: dict[datetime, dict] = {}
        top_talkers: dict[str, dict] = {}
        top_domains: dict[str, dict] = {}

        def _domain_from_url(url: str | None) -> str:
            if not url:
                return "(unknown)"
            try:
                host = urlparse(url).netloc
                return host or "(unknown)"
            except Exception:
                return "(unknown)"

        for log in logs:
            timestamp = log.timestamp
            if timestamp is None:
                continue

            floored_minute = timestamp.minute - (timestamp.minute % bucket_minutes)
            bucket_key = timestamp.replace(minute=floored_minute, second=0, microsecond=0)

            bucket = timeline_buckets.get(bucket_key)
            if bucket is None:
                bucket = {
                    "bucketStart": bucket_key,
                    "events": 0,
                    "bytesOut": 0,
                    "anomalies": 0,
                    "_domainCounts": {},
                }
                timeline_buckets[bucket_key] = bucket

            bytes_sent = int(log.bytes_sent or 0)
            is_anom = bool(log.is_anomaly)
            risk = int(log.risk_score or 0)
            ip = log.client_ip or "(unknown)"
            dom = _domain_from_url(log.url)

            bucket["events"] += 1
            bucket["bytesOut"] += bytes_sent
            if is_anom:
                bucket["anomalies"] += 1
            bucket["_domainCounts"][dom] = bucket["_domainCounts"].get(dom, 0) + 1

            talker = top_talkers.get(ip)
            if talker is None:
                talker = {"clientIp": ip, "events": 0, "bytesOut": 0, "anomalies": 0, "maxRisk": 0}
                top_talkers[ip] = talker
            talker["events"] += 1
            talker["bytesOut"] += bytes_sent
            talker["maxRisk"] = max(talker["maxRisk"], risk)
            if is_anom:
                talker["anomalies"] += 1

            domain = top_domains.get(dom)
            if domain is None:
                domain = {"domain": dom, "events": 0, "bytesOut": 0, "anomalies": 0, "maxRisk": 0}
                top_domains[dom] = domain
            domain["events"] += 1
            domain["bytesOut"] += bytes_sent
            domain["maxRisk"] = max(domain["maxRisk"], risk)
            if is_anom:
                domain["anomalies"] += 1

        # finalize timeline (sorted buckets)
        timeline = []
        for bucket_key in sorted(timeline_buckets.keys()):
            bucket = timeline_buckets[bucket_key]
            top_domains_for_bucket = sorted(bucket["_domainCounts"].items(), key=lambda kv: kv[1], reverse=True)[:3]
            timeline.append({
                "bucketStart": bucket["bucketStart"].isoformat(),
                "events": bucket["events"],
                "bytesOut": bucket["bytesOut"],
                "anomalies": bucket["anomalies"],
                "topDomains": [name for name, _count in top_domains_for_bucket],
            })

        # finalize top talkers and domains
        top_talkers_list = sorted(top_talkers.values(), key=lambda x: (x["bytesOut"], x["events"]), reverse=True)[:top_max]
        top_domains_list = sorted(top_domains.values(), key=lambda x: (x["bytesOut"], x["events"]), reverse=True)[:top_max]

        highlights = []
        if logs:
            biggest = max(logs, key=lambda x: int(x.bytes_sent or 0))
            highlights.append(
                f"Largest outbound transfer: {int(biggest.bytes_sent or 0)} bytes to {_domain_from_url(biggest.url)} (ip={biggest.client_ip})"
            )
        if top_talkers_list:
            highlights.append(
                f"Top talker: {top_talkers_list[0]['clientIp']} ({top_talkers_list[0]['events']} events, {top_talkers_list[0]['bytesOut']} bytes out)"
            )
        anomaly_buckets = [b for b in timeline if b["anomalies"] > 0]
        if anomaly_buckets:
            highlights.append(
                f"Anomalies clustered from {anomaly_buckets[0]['bucketStart']} to {anomaly_buckets[-1]['bucketStart']}"
            )

        return {
            "uploadId": str(upload_id),
            "bucketMinutes": bucket_minutes,
            "timeline": timeline,
            "topTalkers": top_talkers_list,
            "topDomains": top_domains_list,
            "highlights": highlights,
        }