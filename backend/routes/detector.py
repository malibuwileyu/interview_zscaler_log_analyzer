from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from repositories.upload_repository import UploadRepository
from services.upload_service import UploadService
from services.ai_detector_service import AiDetectorService

from models import LogEntry

detector_bp = Blueprint('detector', __name__)

def _log_to_dict(log: LogEntry) -> dict:
    '''Serializes a log entry object to a dictionary.'''
    return {
        'id': str(log.id),
        'upload_id': str(log.upload_id),
        'timestamp': log.timestamp.isoformat(),
        'client_ip': log.client_ip,
        'url': log.url,
        'action': log.action,
        'bytes_sent': log.bytes_sent,
        'risk_score': log.risk_score,
        'is_anomaly': log.is_anomaly,
        'anomaly_note': log.anomaly_note,
    }

@detector_bp.get("/anomalies")
@jwt_required()
def get_anomalies():
    user_id = get_jwt_identity()
    limit = int(request.args.get('limit', 100))
    upload_id = request.args.get('upload_id')

    if upload_id:
        upload = UploadRepository.get_upload_by_id(upload_id)
        if not upload:
            return jsonify({'error': {'code': 'UPLOAD_NOT_FOUND', 'message': 'Upload not found'}}), 404
        if str(upload.user_id) != str(user_id):
            return jsonify({'error': {'code': 'UNAUTHORIZED', 'FORBIDDEN': 'You are not authorized to access this upload'}}), 403
        
        logs = UploadRepository.get_logs_by_upload_id(upload.id, only_anomalies=True, limit=limit)
        return jsonify({'data': {'anomalies': [_log_to_dict(log) for log in logs]}}), 200

    # if no upload_id, get all uploads for the user
    uploads = UploadRepository.get_all_uploads_by_user_id(user_id)
    anomalies = []
    for upload in uploads:  # TODO: optimize this by getting all logs at once
        if len(anomalies) >= limit:
            break
        remaining_limit = limit - len(anomalies)
        logs = UploadRepository.get_logs_by_upload_id(upload.id, only_anomalies=True, limit=remaining_limit)
        anomalies.extend(logs)
        if len(anomalies) >= limit:
            break
    return jsonify({'data': {'anomalies': [_log_to_dict(log) for log in anomalies]}}), 200


@detector_bp.post("/ai/review")
@jwt_required()
def ai_review():
    """
    AI-powered anomaly review for a SMALL batch of logs.

    Body JSON:
    {
      "upload_id": "...",
      "limit": 25,
      "chunk_size": 25,
      "only_anomalies": false
    }
    """
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    upload_id = (data.get("upload_id") or "").strip()
    if not upload_id:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'upload_id is required'}}), 400

    try:
        limit = int(data.get("limit", 25))
    except (TypeError, ValueError):
        limit = 25
    limit = max(1, min(limit, 200))

    try:
        chunk_size = int(data.get("chunk_size", 25))
    except (TypeError, ValueError):
        chunk_size = 25
    chunk_size = max(1, min(chunk_size, 50))

    only_anomalies = bool(data.get("only_anomalies", False))

    upload = UploadRepository.get_upload_by_id(upload_id)
    if not upload:
        return jsonify({'error': {'code': 'UPLOAD_NOT_FOUND', 'message': 'Upload not found'}}), 404
    if str(upload.user_id) != str(user_id):
        return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'You are not authorized to access this upload'}}), 403

    # This endpoint is now READ-ONLY: AI review is generated ONCE on initial upload and persisted.
    # If you call it later, you only get existing results (no new model call).
    logs = UploadRepository.get_logs_by_upload_id(upload_id, only_anomalies=only_anomalies, limit=limit)

    # If AI review hasn't populated yet, return 202 so the UI can poll.
    any_reviewed = any(getattr(l, "ai_reviewed_at", None) for l in logs)
    upload_status = getattr(upload, "ai_review_status", None)
    if upload_status in (None, "Pending") and not any_reviewed:
        return jsonify({"data": {"upload_id": str(upload_id), "status": upload_status or "Pending", "results": []}}), 202

    results = []
    for l in logs:
        results.append(
            {
                "id": str(l.id),
                "is_anomalous": bool(l.ai_is_anomalous) if l.ai_is_anomalous is not None else False,
                "confidence": float(l.ai_confidence or 0.0),
                "reason": str(l.ai_reason or ""),
                "event": _log_to_dict(l),
            }
        )

    return jsonify(
        {
            "data": {
                "upload_id": str(upload_id),
                "model": getattr(upload, "ai_review_model", None),
                "status": upload_status,
                "analyzed_count": len(results),
                "chunk_size": chunk_size,
                "elapsed_ms": None,
                "results": results,
            }
        }
    ), 200