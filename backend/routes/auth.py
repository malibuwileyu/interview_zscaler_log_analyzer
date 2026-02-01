from flask import Blueprint, jsonify, request

from services.auth_service import AuthService
from models import User

auth_bp = Blueprint('auth', __name__)

def _user_to_dict(user: User) -> dict:
    '''Serializes a user object to a dictionary.'''
    return {
        'id': str(user.id),
        'username': user.username
    }

@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'username is required'}}), 400
    
    if not password:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'password is required'}}), 400

    try:
        user = AuthService.register(username=username, password=password)
        return jsonify({'data': {'user': _user_to_dict(user)}}), 201
    except ValueError as e:
        return jsonify({'error': {'code': 'USER_EXISTS', 'message': str(e)}}), 409

@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'username is required'}}), 400
    
    if not password:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'password is required'}}), 400

    try:
        access_token, user = AuthService.login(username=username, password=password)
        return jsonify({'data': {'access_token': access_token, 'user': _user_to_dict(user)}}), 200
    except ValueError as e:
        return jsonify({'error': {'code': 'INVALID_CREDENTIALS', 'message': str(e)}}), 401
