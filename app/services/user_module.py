from app.services.utils import email_validation
from app.services.crud import CRUD
from app.models import User
from app.services.custom_errors import *

crud = CRUD()


def adding_new_users(data: dict) -> str:
    """
    Adding new user through email invitation process
    """
    data["email"] = data["email"].strip().lower()
    email_validation(data['email'])
    user = User.query.filter_by(email = data["email"]).first()
    if not user:
        user = crud.create(User, data)
    elif user and user.registered:
        raise Conflict("This user already registered.")
    token = user.generate_auth_token(3600).decode('ascii')
    crud.update(User, {"email": data["email"]}, {"is_active": True, "registered": False, **data})
    return token


def admin_list_all_users(page: int, per_page: int) -> tuple:
    """
    Admin user view all users in the portal
    """
    # users = User.query.filter(User.user_role != 6).order_by(User.created.desc()).paginate(page, per_page, error_out=False)
    users = User.query.order_by(User.created.desc()).paginate(page, per_page, error_out=False)
    user_info = [u.to_dict() for u in users.items]
    if user_info:
        return user_info, {"total": users.total, "current_page": users.page,
                           "per_page": users.per_page, "length": len(user_info)}
    raise NoContent()


