from flask  import g
from app.models import Project, ProjectUserAssociation, Multimedia
from app.services.crud import CRUD
from app.services.custom_errors import *
from app import db
import boto3
import pytz
from config import Config
from datetime import datetime
from app.services.multimedia import generate_pre_signed_url_multimedia
crud = CRUD()


# def project_manager_validation(user_id: int, project_id: int) -> bool:
#     if not ProjectUserAssociation.query.filter_by(user_id=user_id, project_id=project_id).first():
#         raise Forbidden()
#     return True


def create_project(data: dict, add_users: list) -> bool:
    created = crud.create(Project, {"created_by": g.user['id'], **data})
    for u in add_users:
        crud.create(ProjectUserAssociation, {"user_id": u, "project_id": created.id})
    return True


def edit_project(data: dict, project_id: int, remove_users: list, add_users: list) -> bool:
    if remove_users:
        for u in ProjectUserAssociation.query.filter(ProjectUserAssociation.user_id.in_(remove_users)).all():
            db.session.delete(u)
    if add_users:
        existing_users = [str(i.user_id) for i in ProjectUserAssociation.query.filter_by(project_id=project_id).filter(
            ProjectUserAssociation.user_id.in_(add_users)).all()]
        for u in add_users:
            if u not in existing_users:
                pua = ProjectUserAssociation(project_id = project_id, user_id = u)
                db.session.add(pua)
    if data:
        crud.update(Project, {"id": project_id}, data)
    else:
        crud.db_commit()
    return True


def list_projects(time_zone: str, page: int, per_page: int) -> tuple:
    if g.user['user_role'] == 1:
        project_obj = Project.query.order_by(Project.updated.desc()).paginate(page, per_page, error_out=False)
    else:
        project_obj = Project.query.join(ProjectUserAssociation).filter(
            ProjectUserAssociation.user_id == g.user['id']).order_by(Project.updated.desc()).paginate(page, per_page, error_out=False)
    project_data = [ps.to_dict_list(time_zone) for ps in project_obj.items]
    if project_data:
        return project_data, {"total": project_obj.total, "current_page": project_obj.page, "length": len(project_data),
                              "per_page": project_obj.per_page}
    raise NoContent()


def single_project(time_zone: str, project_id: int) -> dict:
    if g.user['user_role'] == 1:
        p = Project.query.filter_by(id=project_id).first()
    else:
        p = Project.query.filter_by(id=project_id).join(ProjectUserAssociation).filter(
            ProjectUserAssociation.user_id == g.user['id']).first()
    if p:
        data = dict(
            id=p.id,
            name=p.name,
            job_number=p.job_number,
            is_active=p.is_active,
            recording=p.recording,
            client_name=p.client_name,
            media=[],
            creator={"id": p.creator.id, "name": p.creator.name, "user_role": p.creator.user_role},
            created=p.created.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(time_zone)).strftime(
                "%Y-%m-%dT%H:%M:%S"),
            events=[],
            assigned_users=[{'id': u.id, 'user_id': u.user_id, 'name': u.user.name, 'email': u.user.email,
                             'user_role': u.user.user_role} for u in p.assigned_users]
        )
        for e in p.events:
            event_data = dict(
                id=e.id,
                name=e.name,
                event_time=e.event_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(time_zone)).strftime(
                    "%Y-%m-%dT%H:%M:%S") if e.event_time else None,
                state=e.state,
                is_active=e.is_active,
                rooms=len(e.rooms),
                presenters=len([pr for pr in e.presenters if not pr.proj_user_assoc_id])
            )
            if data.get('recording') and event_data.get('presenters') > 0:
                event_data['presenters'] = event_data['presenters'] - 1
            data['events'].append(event_data)
        for m in p.media:
            if (datetime.utcnow()-m.updated).days > 6 or not m.pre_signed_url:
                url = generate_pre_signed_url_multimedia(project_id, m.name, m.type_, m.id)
                crud.update(Multimedia, {"id": m.id}, {"pre_signed_url": url})
            data['media'].append(m.to_dict())
        return data
    raise NoContent()
