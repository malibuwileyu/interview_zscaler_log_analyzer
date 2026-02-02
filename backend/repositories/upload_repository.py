from models import db, LogEntry, Upload
from uuid import UUID

class UploadRepository:
    '''--- Write Operations ---'''
    @staticmethod
    def create_upload(user_id: str, filename: str) -> Upload:
        '''Creates the parent record for a new file upload.'''
        new_upload = Upload(user_id=user_id, filename=filename)
        db.session.add(new_upload)
        db.session.commit()
        # there should definitely be a log entry here
        return new_upload
    
    @staticmethod
    def update_upload_status(upload_id: str, status: str) -> Upload:
        '''Updates the status of an upload (e.g. 'Completed', 'Failed', 'Processing', etc.)'''
        upload = Upload.query.get(upload_id)
        if upload:
            upload.status = status
            db.session.commit()
    
    @staticmethod
    def add_logs_bulk(log_objects: list[LogEntry]) -> None:
        '''High-performance bulk insertion of parsed log entries.'''
        db.session.bulk_insert_mappings(LogEntry, log_objects)
        db.session.commit()

    @staticmethod
    def set_raw_csv_text(upload_id: str, raw_csv_text: str) -> None:
        '''Sets the raw CSV text for an upload.'''
        upload = Upload.query.get(upload_id)
        if upload:
            upload.raw_csv_text = raw_csv_text
            db.session.commit()
    
    '''--- Read Operations ---'''
    @staticmethod
    def get_upload_by_id(upload_id: str) -> Upload:
        '''Retrieves an upload by its ID.'''
        return Upload.query.get(upload_id)
    
    @staticmethod
    def get_logs_by_upload_id(upload_id: str, only_anomalies: bool = False, limit: int = 100) -> list[LogEntry]:
        '''Retrieves all log entries for a given upload ID.'''
        query = LogEntry.query.filter_by(upload_id=upload_id).order_by(LogEntry.timestamp.asc())

        if only_anomalies:
            query = query.filter_by(is_anomaly=True)

        return query.limit(limit).all()

    @staticmethod
    def get_all_uploads_by_user_id(user_id: str) -> list[Upload]:
        '''Retrieves all uploads for a given user ID.'''
        return Upload.query.filter_by(user_id=user_id).all()

    @staticmethod
    def get_all_logs_by_upload_id(upload_id: str) -> list[LogEntry]:
        '''Retrieves all log entries for a given upload ID.'''
        return LogEntry.query.filter_by(upload_id=upload_id).all()
    
    @staticmethod
    def get_all_log_entries() -> list[LogEntry]:
        '''Retrieves all log entries.'''
        return LogEntry.query.all()
    
    @staticmethod
    def get_all_uploads() -> list[Upload]:
        '''Retrieves all uploads.'''
        return Upload.query.all()