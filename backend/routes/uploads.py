from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from repositories.upload_repository import UploadRepository
from services.upload_service import UploadService

from models import Upload, LogEntry

upload_bp = Blueprint('uploads', __name__)

def _upload_to_dict(upload: Upload) -> dict:
    '''Serializes an upload object to a dictionary.'''
    return {
        'id': str(upload.id),
        'user_id': str(upload.user_id),
        'filename': upload.filename,
        'status': upload.status,
    }
    
def _log_to_dict(log: LogEntry) -> dict:
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

@upload_bp.post("/")
@jwt_required()
def create_upload():
    user_id = get_jwt_identity()

    file_storage = request.files.get('file')
    if not file_storage:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'missing multipart form field: file'}}), 400

    try:
        upload = UploadService.process_log_file(file_storage=file_storage, user_id=user_id)
        return jsonify({'data': {'upload': _upload_to_dict(upload)}}), 201
    except ValueError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except Exception as e:
        # TODO: log the error
        return jsonify({'error': {'code': 'UPLOAD_FAILED', 'message': str(e)}}), 500

@upload_bp.get("/")
@jwt_required()
def list_uploads():
    user_id = get_jwt_identity()
    uploads = UploadRepository.get_all_uploads_by_user_id(user_id)
    return jsonify({'data': {'uploads': [_upload_to_dict(upload) for upload in uploads]}}), 200

@upload_bp.get("/<upload_id>/logs")
@jwt_required()
def list_logs(upload_id):
    user_id = get_jwt_identity()
    upload = UploadRepository.get_upload_by_id(upload_id)

    if not upload:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Upload not found'}}), 404
    if str(upload.user_id) != str(user_id):
        return jsonify({'error': {'code': 'UNAUTHORIZED', 'FORBIDDEN': 'You are not authorized to access this upload'}}), 403

    only_anomalies = request.args.get('only_anomalies', '0') in ('1', 'true', 'True')
    limit = int(request.args.get('limit', '100'))

    logs = UploadRepository.get_logs_by_upload_id(upload_id, only_anomalies=only_anomalies, limit=limit)
    return jsonify({'data': {'logs': [_log_to_dict(log) for log in logs]}}), 200

@upload_bp.get("/<upload_id>/summary")
@jwt_required()
def get_upload_summary(upload_id):
    user_id = get_jwt_identity()
    upload = UploadRepository.get_upload_by_id(upload_id)
    if not upload:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Upload not found'}}), 404
    if str(upload.user_id) != str(user_id):
        return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'You are not authorized to access this upload'}}), 403

    try:
        bucket_minutes = int(request.args.get("bucket_minutes", "5"))
        if bucket_minutes <= 0:
            raise ValueError("bucket_minutes must be a positive integer")
        if bucket_minutes > 60:
            raise ValueError("bucket_minutes must be less than or equal to 60")
    except (ValueError, TypeError):
        bucket_minutes = 5
    summary = UploadService.get_upload_summary(upload_id, bucket_minutes=bucket_minutes)
    return jsonify({'data': {'summary': summary}}), 200