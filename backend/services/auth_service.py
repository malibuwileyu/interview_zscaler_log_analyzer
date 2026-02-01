from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from models import User
from repositories.user_repository import UserRepository

class AuthService:
    '''--- Write Operations ---'''
    @staticmethod
    def register(username: str, password: str) -> User:
        '''Registers a new user.'''
        if UserRepository.get_user_by_username(username):
            raise ValueError("User already exists")
        
        password_hash = generate_password_hash(password)
        user = UserRepository.create_user(username, password_hash)
        return user

    @staticmethod
    def login(username: str, password: str) -> tuple[str, User]: 
        user = UserRepository.get_user_by_username(username)
        if not user or not check_password_hash(user.password_hash, password):
            raise ValueError("Invalid username or password")
        access_token = create_access_token(identity=str(user.id))
        return access_token, user