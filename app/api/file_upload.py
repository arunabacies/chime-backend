from flask import jsonify, request, g
from app.services.crud import CRUD
from app.api.user import tokenAuth
from app.models.multimedia import Multimedia
from app.services.multimedia import multimedia_upload, delete_proj_multimedia
from app.services.auth import admin_user_authorizer
from app.services.custom_errors import *
from app.api import bp
crud = CRUD()

@bp.route('/project/multimedia_uploader/<int:project_id>', methods=["POST"])
@tokenAuth.login_required
def upload_multimedia_files(project_id):
    file = request.files['file']
    print(file)
    if request.args.get('id_'):
        delete_proj_multimedia(project_id, request.args.get('id_'))
    multimedia_upload(file, project_id)
    return jsonify({"message": "Uploaded successfully", "status": 200}), 200

@bp.route('/project/multimedia/<int:id_>', methods=["DELETE"])
@tokenAuth.login_required
def delete_multimedia(id_):
    delete_proj_multimedia(request.args.get('project_id'), id_)
    return jsonify({"message": "successfully Deleted", "status": 200}), 200
