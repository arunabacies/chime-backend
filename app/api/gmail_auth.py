from flask import Flask, redirect, url_for, session, request, jsonify
from authlib.integrations.flask_client import OAuth
import json
import app
from app.services.custom_errors import *
from config import Config
from app.api import bp
from app.services.crud import CRUD
from app.models import User, Studio
# import app
# from app import create_app
# app =create_app()
# app.app_context().push()
crud = CRUD()
# oAuth Setup
# print(dir(app))
oauth = OAuth(app.app)
google = oauth.register(
    name='google',
    client_id=Config.GOOGLE_CLIENT_ID,
    client_secret=Config.GOOGLE_CLIENT_SECRET,
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/v2/auth?access_type=offline&prompt=consent',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    # This is only needed if using openId to fetch user info
    client_kwargs={
        'scope': 'https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/userinfo.email'}
)


@bp.route('/google/index')
def gmail_index():
    return "Successfully completed your gmail authentication"


@bp.route('/google/login')
def login():
    u = User.verify_auth_token(request.args.get("token").strip())
    if not u:
        raise Unauthorized()
    session['user'] = u
    session['studio'] = request.args.get('studio_id')
    google = oauth.create_client('google')  # create the google oauth client
    redirect_uri = url_for('api.gmail_authorize', _external=True)
    return google.authorize_redirect(redirect_uri.replace("http://", "https://"))


@bp.route('/google/authorized')
def gmail_authorize():
    google = oauth.create_client('google')  # create the google oauth client
    token = google.authorize_access_token()  # Access token from google (needed to get user info)
    resp = google.get('userinfo')  # userinfo contains stuff u specified in the scope
    user_info = resp.json()
    print(json.dumps(token))
    st = Studio.query.filter_by(id=session['studio']).first()
    if session['user']['user_role'] != 1:
        if st.created_by != session['user']['id']:
            raise Forbidden()
    st.storage_source = 2
    st.storage_credential = json.dumps({"email": user_info.get("email").lower(), "o_data": token})
    crud.db_commit()
    redirect_uri = url_for('api.gmail_index', _external=True)
    return redirect(redirect_uri.replace("http://", "https://"))