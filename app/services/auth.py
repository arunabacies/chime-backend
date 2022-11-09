from flask import g
from app.models import User
from app import db
from functools import wraps
from app.services.custom_errors import *
from app.services.crud import CRUD

crud = CRUD()


class AuthService(object):

    def forgot_password(self, email: str, time=3600) -> str:
        user = User.query.filter_by(email=email, is_active=True).first()
        if not user:
            raise NoContent("Please enter a valid email address.")
        if not user.registered:
            raise Forbidden("Please register first")
        token = user.generate_auth_token(time).decode('ascii')
        return token

    def new_invitee(self, data: dict) -> bool:
        """
        User registration from email invitation
        """
        user = User.query.filter_by(id=g.user['id']).first()
        user.hash_password(data["password"].strip())
        user.is_active = True
        user.registered = True
        if data.get('name'):
            user.name = data.get("name")
        db.session.add(user)
        crud.db_commit()
        return True

    def new_password(self, user_id: int, password: str) -> bool:
        user = User.query.get(user_id)
        user.hash_password(password)
        db.session.add(user)
        return crud.db_commit()


def admin_user_authorizer(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if g.user['user_role'] == 1:
            return func(*args, **kwargs)
        raise Forbidden()

    return inner


# def admin_or_manager_authorizer(func):
#     @wraps(func)
#     def inner(*args, **kwargs):
#         if g.user['user_role'] in [1, 2]:
#             return func(*args, **kwargs)
#         raise Forbidden()
#
#     return inner
