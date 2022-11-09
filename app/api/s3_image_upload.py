from flask import jsonify, request, g, render_template
from app.services.crud import *
from app.models.projects import Project, ProjectUserAssociation
from config import Config
from app.api.user import tokenAuth
from app.services.auth import admin_user_authorizer
from app.models.presenter import Presenter
from app.services.projects_service import create_project, edit_project, list_projects, single_project
from app.api import bp
import uuid
import boto3
crud = CRUD()


@bp.route("/file_uploader")
def uploader_test():
    return render_template("s3_uploader.html")


@bp.route('/upload_avatar', methods=["POST"])
@tokenAuth.login_required
@admin_user_authorizer
def upload_file_to_s3():
    """
    Upload images
    """
    image_file = request.files['file']
    file_name = f"{request.args.get('uid')}-{uuid.uuid4()}"
    print(image_file, file_name)
    client = boto3.client('s3',
                          region_name=Config.BUCKET_REGION,
                          aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY)
    print(client)
    client.put_object(Body=image_file, Bucket=Config.AVATAR_BUCKET_NAME,
                      Key=file_name, ContentType=request.mimetype)
    print(client)
    return jsonify({"data": {"avatar": f"https://{Config.AVATAR_BUCKET_NAME}.s3.{Config.BUCKET_REGION}.amazonaws.com/"
                                       f"{file_name}"}, "message": "Success", "status": 200}), 200
