from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from repositories.upload_repository import UploadRepository
from services.upload_service import UploadService

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