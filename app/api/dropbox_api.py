import re
from flask import Flask, redirect, url_for, jsonify, session
from flask.globals import request
from flask.wrappers import JSONMixin
from flask_dance.contrib.dropbox import make_dropbox_blueprint, dropbox
from app.models import User, Studio
from config import Config
from app.services.crud import CRUD
from app.services.custom_errors import *
import json


crud = CRUD()

dropbox_blueprint = make_dropbox_blueprint(
    app_key=Config.DROPBOX_APP_KEY,
    app_secret=Config.DROPBOX_APP_SECRET,
    redirect_url="/dropbox/success"
)


@dropbox_blueprint.route("/dropbox/login")
def dropbox_index():
    u = User.verify_auth_token(request.args.get("token").strip())
    if not u:
        raise Unauthorized()
    session['user'] = u
    session['studio'] = request.args.get('studio_id')
    if not dropbox.authorized:
        print(dir(dropbox))
        print(url_for("dropbox.login"))
        # url = url_for("dropbox.login")
        return redirect(url_for("dropbox.login"))
    print(dropbox.token)
    dropbox_process_data(dropbox)
    return "You are successfully logged in"


@dropbox_blueprint.route("/dropbox/success")
def test_get():
    print(dropbox.token)
    dropbox_process_data(dropbox)
    return jsonify({"message": "Success"}), 200


def dropbox_process_data(dropbox):
    resp = dropbox.post("users/get_current_account")
    st = Studio.query.filter_by(id=session['studio']).first()
    if session['user']['user_role'] != 1:
        if st.created_by != session['user']['id']:
            raise Forbidden()
    st.storage_source = 3
    st.storage_credential = json.dumps({"email": resp.json().get('email'), "o_data": dropbox.token})
    crud.db_commit()
    return True