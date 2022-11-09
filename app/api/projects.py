import json
from flask import jsonify, request, g
from app.services.crud import *
from app.models.projects import Project, ProjectUserAssociation
from app.api.user import tokenAuth
from app.services.auth import admin_user_authorizer
from app.services.projects_service import create_project, edit_project, list_projects, single_project
from app.api import bp

crud = CRUD()


@bp.route('/project/add', methods=["POST"])
@tokenAuth.login_required
@admin_user_authorizer
def post_project():
    print(f"Post project: {request.json}")
    create_project(request.json, request.json.pop("add_users"))
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/project/edit/<int:project_id>', methods=["PUT"])
@tokenAuth.login_required
@admin_user_authorizer
def put_project(project_id):
    print(f"Put project: {request.json}")
    # if g.user['user_role'] == 2:
    #     project_manager_validation(g.user['id'], project_id)
    edit_project(request.json, project_id, request.json.pop("remove_users"), request.json.pop("add_users"))
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/project/assigned_user_del/<int:project_id>', methods=["DELETE"])
@tokenAuth.login_required
def delete_project_user(project_id):
    if g.user['user_role'] == 1 or Project.query.filter_by(id=project_id, created_by=g.user['id']).first():
        crud.delete(ProjectUserAssociation, {"project_id": project_id, "user_id": request.args.get('user_id')})
        return jsonify({"message": "Success", "status": 200}), 200
    raise Forbidden()


@bp.route('/project/delete/<int:project_id>', methods=["DELETE"])
@tokenAuth.login_required
@admin_user_authorizer
def delete_project(project_id):
    # if g.user['user_role'] == 2:
    #     project_manager_validation(g.user['id'], project_id)
    crud.delete(Project, {"id": project_id})
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/project/list', methods=["GET"])
@tokenAuth.login_required
def get_project_list():
    data = list_projects(request.args['time_zone'], int(request.args.get("page", 1)),
                         int(request.args.get("per_page", 6)))
    return jsonify({"data": data[0], "message": "Success", "status": 200, "pagination": data[1]}), 200


@bp.route('/project/get_single_project/<int:project_id>', methods=["GET"])
@tokenAuth.login_required
def get_single_project(project_id):
    print(f"Get single project : {request.args}")
    result = single_project(request.args['time_zone'], project_id)
    print(result)
    return jsonify({"data": result, "message": "Success", "status": 200}), 200


@bp.route('/project/event/<int:project_id>', methods=["DELETE"])
@tokenAuth.login_required
@admin_user_authorizer
def delete_user_from_project(project_id):
    print(request.args)
    if g.user['user_id'] == request.args.get('user_id'):
        raise UnProcessable("Sorry you cannot delete yourself")
    crud.delete(ProjectUserAssociation, {"project_id": project_id, "user_id": request.args.get('user_id')})
    return jsonify({"message": "Success", "status": 200}), 200

