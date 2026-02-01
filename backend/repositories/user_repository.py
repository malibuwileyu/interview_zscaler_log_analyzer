from models import db, User
from uuid import UUID

class UserRepository:
    '''--- Write Operations ---'''
    @staticmethod
    def create_user(username: str, password_hash: str) -> User:
        '''Creates a new user.'''
        new_user = User(username=username, password_hash=password_hash)
        db.session.add(new_user)
        db.session.commit()
        return new_user
    
    '''--- Read Operations ---'''
    @staticmethod
    def get_user_by_username(username: str) -> User:
        '''Retrieves a user by their username.'''
        return User.query.filter_by(username=username).first()
    
    @staticmethod
    def get_user_by_id(user_id: UUID) -> User:
        '''Retrieves a user by their ID.'''
        return User.query.get(user_id)