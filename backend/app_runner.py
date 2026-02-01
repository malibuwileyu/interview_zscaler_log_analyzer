import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from sqlalchemy import text

from models import db

from routes.auth import auth_bp
from routes.uploads import upload_bp
from routes.detector import detector_bp

def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__)

    # --- Config --- 
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'postgres://localhost:5432/log_analyzer')

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

    expires_seconds = os.getenv('JWT_ACCESS_TOKEN_EXPIRES') or '3600'
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(seconds=int(expires_seconds))
    
    # TODO add refresh token expiration (and refresh token)
    app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH_BYTES', str(25 * 1024 * 1024)))

    db.init_app(app)

    with app.app_context():
        db.create_all()
        db.session.execute(text("SELECT 1"))

    Migrate(app, db)
    JWTManager(app)
    CORS(
        app,
        resources={r'/*': {'origins': os.getenv('CORS_ORIGINS', '*')}},
        supports_credentials=True,
    )

    # --- Health ---
    @app.get('/health')
    def health():
        return jsonify({'status': 'ok'})

    # --- Routes ---
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(upload_bp, url_prefix='/api/uploads')
    app.register_blueprint(detector_bp, url_prefix='/api/detector')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(
        host='0.0.0.0', 
        port=int(os.getenv('PORT', '5000')), 
        debug=os.getenv('FLASK_DEBUG', '1') == '1'
    )