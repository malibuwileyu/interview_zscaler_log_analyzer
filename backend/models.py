"""
Database models for the application. Generated with AI using a db schema as input.

User:
- id: UUID
- username: String
- password_hash: String
- uploads: relationship to Upload

Upload:
- id: UUID
- user_id: UUID
- filename: String
- status: String
- log_entries: relationship to LogEntry

LogEntry:
- id: UUID
- upload_id: UUID
- timestamp: DateTime
- client_ip: String
- url: String
- action: String
- bytes_sent: Integer
- risk_score: Float
- is_anomaly: Boolean
- anomaly_note: String
"""
import uuid
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    uploads = db.relationship("Upload", back_populates="user", cascade='all, delete-orphan')

class Upload(db.Model):
    __tablename__ = 'uploads'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Processing')

    raw_csv_text = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)

    ai_review_status = db.Column(db.String(32), nullable=True)  # Pending | Completed | Failed
    ai_review_model = db.Column(db.String(128), nullable=True)
    ai_reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    ai_review_error = db.Column(db.Text, nullable=True)
    
    user = db.relationship("User", back_populates="uploads")
    log_entries = db.relationship("LogEntry", back_populates="upload", cascade='all, delete-orphan')

class LogEntry(db.Model):
    __tablename__ = 'log_entries'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id = db.Column(UUID(as_uuid=True), db.ForeignKey('uploads.id', ondelete="CASCADE"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False) # ZScaler timestamp
    client_ip = db.Column(db.String(45), nullable=False)
    url = db.Column(db.Text, nullable=False) # Use Text for URLs as they can be long
    action = db.Column(db.String(100), nullable=False)
    bytes_sent = db.Column(db.BigInteger, nullable=False, default=0) # Logs use big numbers
    risk_score = db.Column(db.Integer, nullable=True)
    is_anomaly = db.Column(db.Boolean, nullable=False, default=False)
    anomaly_note = db.Column(db.String(512), nullable=True)
    confidence_score = db.Column(db.Float, nullable=True)

    # Persisted AI review decision (optional; may be null until AI review completes)
    ai_is_anomalous = db.Column(db.Boolean, nullable=True)
    ai_confidence = db.Column(db.Float, nullable=True)
    ai_reason = db.Column(db.Text, nullable=True)
    ai_model = db.Column(db.String(128), nullable=True)
    ai_reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    upload = db.relationship("Upload", back_populates="log_entries")