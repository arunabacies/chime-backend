from flask import request, jsonify, g, render_template
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
from app.models import User
from app import db
from app.services.auth import (AuthService, admin_user_authorizer)
from app.services.user_module import (adding_new_users, admin_list_all_users)
from config import Config
from app.services.crud import CRUD
from app.services.custom_errors import *
from app.services.sendgrid_email import send_email
from app.api import bp
from datetime import datetime
from app.services.multimedia import (upload_user_profile_pic, delete_s3_object, generate_session_url)
auth = HTTPBasicAuth()
tokenAuth = HTTPTokenAuth(scheme='Token')
auth_service = AuthService()
crud = CRUD()


@auth.verify_password
def verify_password(email, password):
    user = User.query.filter_by(email=email, is_active=True).first()
    if user:
        if not user.registered:
            raise Unauthorized("Please register first and try again")
        elif user.check_password(password):
            g.user = user
            return True
    raise BadRequest("Incorrect Email or Password")


@tokenAuth.verify_token
def verify_token(token):
    user = User.verify_auth_token(token)
    if user:
        g.user = user
        return True
    raise Unauthorized()


@bp.route('/user/edit_user_details/<int:user_id>', methods=["PUT"])
@tokenAuth.login_required
def change_user_info(user_id):
    data = request.form.to_dict()
    print(data)
    if g.user['user_role'] != 1 and g.user['id'] != user_id:
        raise Forbidden()
    if data.get("avatar_file_name"):
        delete_s3_object(f"avatar/{data.pop('avatar_file_name')}")
        data.update({"avatar_file_name": "", "avatar": ""})
    if request.files:
        file = request.files['file']
        avatar = upload_user_profile_pic(user_id, file)
        print(f"avatar is {avatar}")
        data.update(avatar)
    crud.update(User, {"id": user_id}, data)
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/admin/invite_new_user', methods=['POST'])
@tokenAuth.login_required
def add_new_users():
    print(f"Adding new user: {request.json}")
    if g.user['user_role'] != 1:
        raise Forbidden()
    token = adding_new_users(request.json)
    invitation_html = render_template("user_invitation.html",
                                      registration_url=f"{Config.FRONT_END_REGISTRATION_URL}{token}?name="
                                                       f"{request.json['name']}")
    if token and send_email(to_email=request.json["email"].lower(), html_content=invitation_html, subject="Invitation"):
        return jsonify({"message": "success", "status": 200}), 200
    raise InternalError("Please try again later.")


@bp.route('/user/registration_from_invitation', methods=['PUT'])
@tokenAuth.login_required
def user_registration_invitee():
    print(f"Form data: {request.form}")
    print(request.files)
    data = request.form
    if data.get("password") != data.get("confirm_password") or not data.get("password"):
        raise BadRequest("Password Mismatch.")
    auth_service.new_invitee(data)
    if request.files:
        file = request.files['file']
        print(file)
        avatar = upload_user_profile_pic(g.user['id'], file)
        crud.update(User, {"id": g.user['id']}, avatar)
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/user/login', methods=['POST'])
def get_auth_token():
    print(f"User login {request.json}")
    verify_password(request.json.get('email', ' ').lower().strip(), request.json.get('password', ' ').strip())
    token = g.user.generate_auth_token(Config.AUTH_TOKEN_EXPIRES).decode('ascii')
    if g.user.avatar_file_name:
        g.user.avatar_start_time = datetime.utcnow()
        g.user.avatar = generate_session_url(f"avatar/{g.user.avatar_file_name}")
    db.session.add(g.user)
    crud.db_commit()
    print(g.user)
    return jsonify(
        {"auth_token": token, "data": g.user.to_dict(), "status": 200}), 200


@bp.route('/user/forgot_password', methods=['POST'])
def forgot_password():
    print(f"forgot password: {request.json}")
    token = auth_service.forgot_password(request.json.get("email").lower())
    password_reset_form = render_template("reset_template.html",
                                          reset_url=f"{Config.FRONT_END_PASSWORD_RESET_URL}{token}")
    if send_email(to_email=request.json.get("email").lower(), html_content=password_reset_form,
                  subject="Reset Password"):
        return jsonify({"message": "Please check your email", "status": 200}), 200
    raise InternalError()


@bp.route('/user/reset_password', methods=['PATCH'])
@tokenAuth.login_required
def reset_password():
    print(f"Reset password: {request.json}")
    if not request.json.get("new_password") or not request.json.get("confirm_password") or \
            request.json.get("new_password") != request.json.get("confirm_password"):
        raise BadRequest("Enter the new password correctly.")
    if auth_service.new_password(g.user['id'], request.json["new_password"]):
        return jsonify({"message": "Password has been changed successfully", "status": 200}), 200
    return InternalError()


@bp.route('/admin/list_users', methods=["GET"])
@tokenAuth.login_required
@admin_user_authorizer
def admin_list_all_users_data():
    print(f"admin list users: {request.args}")
    data = admin_list_all_users(int(request.args.get("page", 1)), int(request.args.get("per_page", 10)))
    return jsonify({"data": data[0], "pagination": data[1], "message": "Success", "status": 200}), 200


@bp.route('/user/list_users', methods=["GET"])
@tokenAuth.login_required
def user_list_all_users_data():
    print(f"list users {request.args}")
    if request.args.get("user_role"):
        data = [{"id": u.id, "name": u.name, "user_role": u.user_role} for u in User.query.filter_by(user_role=request.args.get("user_role"), is_active=True).all()]
    else:
        # data = [{"id": u.id, "name": u.name, "user_role": u.user_role} for u in User.query.filter(User.user_role!=6, User.is_active==True).all()]
        data = [{"id": u.id, "name": u.name, "user_role": u.user_role} for u in User.query.filter(User.is_active==True).all()]
    return jsonify({"data": data, "message": "Success", "status": 200}), 200


@bp.route('/user/my_profile', methods=["GET"])
@tokenAuth.login_required
def get_my_profile():
    u = User.query.filter_by(id=g.user['id']).first()
    if u.avatar_file_name and (datetime.utcnow()-u.avatar_start_time).days>6:
        u.avatar_start_time = datetime.utcnow()
        u.avatar = generate_session_url(f"{Config.S3_MULTIMEDIA_BUCKET}/avatar/{u.avatar_file_name}")
        crud.db_commit()
    return jsonify({"data": u.to_dict(), "message": "Success", "status": 200}), 200


@bp.route('/admin/delete_user/<int:user_id>', methods=["DELETE"])
@tokenAuth.login_required
@admin_user_authorizer
def delete_single_user(user_id):
    if g.user['id'] == user_id:
        raise BadRequest("You cannot delete your profile.")
    crud.delete(User, {"id": user_id})
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/user/filter_by_role', methods=["GET"])
@tokenAuth.login_required
@admin_user_authorizer
def filter_by_role_user():
    data = [{'id': u.id, 'name': u.name} for u in User.query.filter_by(user_role=request.args.get('user_role')).all()]
    return jsonify({"data": data, "message": "Success", "status": 200}), 200

