from __future__ import annotations

import csv
import io
from werkzeug.datastructures import FileStorage
from datetime import datetime

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
            stream = io.StringIO(file_storage.stream.read().decode('utf-8'), newline=None)
            reader = csv.DictReader(stream)

            UploadService._validate_headers(reader.fieldnames)

            parsed_logs = []
            for row in reader:
                is_anomaly, reason = UploadService.parse_log_row(row)

                parsed_logs.append({
                    'upload_id': upload.id,
                    'timestamp': UploadService._parse_timestamp(row.get('datetime')),
                    'client_ip': row.get('clientip'),
                    'url': row.get('url'),
                    'action': row.get('action'),
                    'bytes_sent': int(row.get('sentbytes', 0)),
                    'risk_score': int(row.get('app_risk_score', 0)),
                    'is_anomaly': is_anomaly,
                    'anomaly_note': reason
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
    def parse_log_row(row: dict) -> tuple[bool, str]:
        '''Parses a single log row and determines if it is an anomaly.'''
        reasons = []
        if int(row.get('app_risk_score', 0)) >= 4:
            reasons.append("High risk app")
        if int(row.get('sentbytes', 0)) > 5000000:
            reasons.append("Large data outbound")

        return len(reasons) > 0, ", ".join(reasons)