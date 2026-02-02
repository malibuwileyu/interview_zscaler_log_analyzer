from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass
from typing import Any

from models import LogEntry


@dataclass(frozen=True)
class AiDecision:
    id: str
    is_anomalous: bool
    confidence: float
    reason: str


class AiDetectorService:
    """
    Minimal OpenAI-backed anomaly review.

    - No new frameworks: uses stdlib urllib.
    - Operates on small batches ("chunks") so the model stays focused.
    - Returns strict per-log decisions: yes/no + short reason + confidence 0..1
    """

    @staticmethod
    def review_logs(
        logs: list[LogEntry],
        *,
        chunk_size: int = 25,
        model: str | None = None,
        max_reason_chars: int = 220,
    ) -> dict[str, Any]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Missing required env var: OPENAI_API_KEY")

        model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")

        if chunk_size <= 0:
            chunk_size = 25
        chunk_size = min(chunk_size, 50)

        # Serialize minimal event fields (keep token usage reasonable).
        events: list[dict[str, Any]] = []
        for l in logs:
            events.append(
                {
                    "id": str(l.id),
                    "timestamp": l.timestamp.isoformat() if l.timestamp else None,
                    "client_ip": l.client_ip,
                    "url": l.url,
                    "action": l.action,
                    "bytes_sent": int(l.bytes_sent or 0),
                    "risk_score": int(l.risk_score or 0) if l.risk_score is not None else None,
                    "heuristic_is_anomaly": bool(l.is_anomaly),
                    "heuristic_note": l.anomaly_note,
                    "heuristic_confidence": float(l.confidence_score or 0.0),
                }
            )

        decisions: dict[str, AiDecision] = {}
        started = time.time()

        for i in range(0, len(events), chunk_size):
            chunk = events[i : i + chunk_size]
            chunk_decisions = AiDetectorService._review_chunk(
                chunk,
                api_key=api_key,
                base_url=base_url,
                model=model,
                max_reason_chars=max_reason_chars,
            )
            for d in chunk_decisions:
                decisions[d.id] = d

        elapsed_ms = int((time.time() - started) * 1000)
        return {
            "model": model,
            "chunk_size": chunk_size,
            "elapsed_ms": elapsed_ms,
            "decisions": [
                {
                    "id": d.id,
                    "is_anomalous": d.is_anomalous,
                    "confidence": d.confidence,
                    "reason": d.reason,
                }
                for d in decisions.values()
            ],
        }

    @staticmethod
    def _review_chunk(
        chunk: list[dict[str, Any]],
        *,
        api_key: str,
        base_url: str,
        model: str,
        max_reason_chars: int,
    ) -> list[AiDecision]:
        system_prompt = (
            "You are a senior cybersecurity SOC analyst reviewing web proxy logs.\n"
            "Goal: for each event, decide if it is anomalous in context.\n"
            "Important:\n"
            "- Do NOT treat 'high risk score' or 'large bytes' as automatically anomalous.\n"
            "- Use destination URL/domain context (e.g., IT/admin tooling vs consumer file share vs paste sites).\n"
            "- Produce a per-event yes/no decision, a short reason, and a confidence score.\n"
            "- Keep reasons concise and actionable.\n"
            "\n"
            "Output MUST be valid JSON only (no markdown) with this exact shape:\n"
            "{\n"
            '  "results": [\n'
            '    {"id": "<id>", "is_anomalous": true|false, "confidence": 0.0-1.0, "reason": "<string>"}\n'
            "  ]\n"
            "}\n"
        )

        user_prompt = (
            "Review the following log events.\n"
            "Return JSON with one result per input event id.\n"
            f"Reason must be <= {max_reason_chars} characters.\n"
            "\n"
            "Events JSON:\n"
            + json.dumps(chunk, ensure_ascii=False)
        )

        payload = {
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }

        raw = AiDetectorService._post_json(
            url=f"{base_url.rstrip('/')}/v1/chat/completions",
            api_key=api_key,
            payload=payload,
            timeout_seconds=int(os.getenv("OPENAI_TIMEOUT_SECONDS", "30")),
        )

        content = (
            raw.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        try:
            parsed = json.loads(content)
        except Exception as e:
            raise RuntimeError(f"OpenAI returned non-JSON content: {content[:200]}") from e

        results = parsed.get("results", [])
        if not isinstance(results, list):
            raise RuntimeError("OpenAI JSON missing 'results' list")

        decisions: list[AiDecision] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            id_val = str(item.get("id") or "")
            if not id_val:
                continue
            is_anom = bool(item.get("is_anomalous"))
            conf = float(item.get("confidence") or 0.0)
            conf = max(0.0, min(1.0, conf))
            reason = str(item.get("reason") or "").strip()
            if len(reason) > max_reason_chars:
                reason = reason[: max_reason_chars - 1] + "…"
            decisions.append(AiDecision(id=id_val, is_anomalous=is_anom, confidence=conf, reason=reason))

        # Ensure every input id has an output (fill missing with conservative defaults).
        seen = {d.id for d in decisions}
        for ev in chunk:
            ev_id = str(ev.get("id") or "")
            if ev_id and ev_id not in seen:
                decisions.append(
                    AiDecision(
                        id=ev_id,
                        is_anomalous=False,
                        confidence=0.0,
                        reason="No AI decision returned for this event.",
                    )
                )
        return decisions

    @staticmethod
    def _post_json(*, url: str, api_key: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url=url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                body = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            raise RuntimeError(f"OpenAI request failed: {e}") from e

        try:
            parsed = json.loads(body)
        except Exception as e:
            raise RuntimeError(f"OpenAI returned non-JSON response: {body[:200]}") from e

        # Surface API errors clearly
        if isinstance(parsed, dict) and "error" in parsed:
            raise RuntimeError(f"OpenAI API error: {parsed['error']}")

        return parsed


