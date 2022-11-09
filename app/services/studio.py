from operator import add
from flask import g
from app.models import Studio, StudioSession, StudioUserAssociation, StudioPresenter, StudioSessionMember
from app.services.crud import CRUD
from app.services.presenter import twilio_create_new_stun_server
from app.services.multimedia import generate_session_url, resource_s3
from app.services.custom_errors import *
from app import db
import pytz
from config import Config
from datetime import datetime
import re
import uuid
import json
import string
import random
from app.services.dropbox_services import DropBox
crud = CRUD()


def create_studio(data: dict, add_users: list) -> bool:
    """
    Create new studio and can assign crew members to the project
    """
    created = crud.create(Studio, {"created_by": g.user['id'], **data})
    for u in add_users:
        member = StudioUserAssociation(user_id=u, studio_id=created.id)
        db.session.add(member)
    if add_users:
        crud.db_commit()
    return True


def edit_studio(data: dict, studio_id: int, remove_users: list, add_users: list) -> bool:
    """
    Edit studio details
    Remove members from the studio
    Add new members to the studio
    """
    print(data)
    print(remove_users)
    print(add_users)
    for u in StudioUserAssociation.query.filter_by(studio_id=studio_id).filter(StudioUserAssociation.user_id.in_(
            remove_users)).all():
        print(f"removing user {u}")
        db.session.delete(u)
    if add_users:
        existing_users = set(str(i.user_id) for i in StudioUserAssociation.query.filter_by(studio_id=studio_id).filter(
            StudioUserAssociation.user_id.in_(add_users)).all())
        if existing_users:
            add_users = list(set(add_users) - existing_users)
        for u in add_users:
            member = StudioUserAssociation(user_id=u, studio_id=studio_id)
            db.session.add(member)
    if data:
        crud.update(Studio, {"id": studio_id}, data)
    else:
        crud.db_commit()
    return True


def list_studios(time_zone: str, page: int, per_page: int) -> tuple:
    if g.user['user_role'] == 1:
        studio_obj = Studio.query.order_by(Studio.updated.desc()).paginate(page, per_page, error_out=False)
    else:
        studio_obj = Studio.query.join(StudioUserAssociation).filter(
            StudioUserAssociation.user_id == g.user['id']).order_by(Studio.updated.desc()).paginate(
            page, per_page, error_out=False)
    studio_data = [ps.to_dict_list(time_zone) for ps in studio_obj.items]
    if studio_data:
        return studio_data, {"total": studio_obj.total, "current_page": studio_obj.page, "length": len(studio_data),
                             "per_page": studio_obj.per_page}
    raise NoContent()


def single_studio(time_zone: str, studio_id: int) -> dict:
    if g.user['user_role'] == 1:
        st = Studio.query.filter_by(id=studio_id).first()
    else:
        st = Studio.query.filter_by(id=studio_id).join(StudioUserAssociation).filter(StudioUserAssociation.user_id == g.user['id']).first()
    if st:
        data = dict(
            id=st.id,
            name=st.name,
            job_number=st.job_number,
            is_active=st.is_active,
            recording=st.recording,
            client_name=st.client_name,
            creator={"id": st.creator.id, "name": st.creator.name, "user_role": st.creator.user_role},
            created_at=st.created.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(time_zone)).strftime(
                "%Y-%m-%dT%H:%M:%S"),
            sessions=[],
            assigned_users=[{'id': u.id, 'user_id': u.user_id, 'name': u.user.name, 'email': u.user.email,
                             'user_role': u.user.user_role} for u in st.assigned_users]
        )
        for s in st.sessions:
            session_data = dict(
                id=s.id,
                name=s.name,
                session_time=s.session_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(time_zone)).strftime(
                    "%Y-%m-%dT%H:%M:%S") if s.session_time else None,
                state=s.state,
                start_recording=s.start_recording,
                is_active=s.is_active,
                presenters=0,
                recordings=0
            )
            for pr in s.presenters:
                if not pr.session_user_assoc_id and pr.name != "ScreenRecorderBot":
                    session_data['presenters'] += 1
                    if pr.started_recording or pr.stored:
                        session_data['recordings'] += 1
            data['sessions'].append(session_data)
        return data
    raise NoContent()


def add_members_to_session(add_members: list, session_id: int, studio_id: int):
    """
    Add members to the studio session
    """
    studio_members = {m.id: {"user_id": m.user_id, "name": m.user.name} for m in StudioUserAssociation.query.filter_by(
        studio_id=studio_id).all()}
    for u in add_members:
        m = crud.create(StudioSessionMember, {"studio_session_id": session_id,  **u})
        pr = StudioPresenter(
            session_id=session_id, is_active=False, session_user_assoc_id=m.id,
            external_user_id=f"{str(random.random())[2:8]}#{studio_members[u['studio_user_id']]['name'].split()[0]}",
            password=f"{''.join(i for i in random.sample(string.ascii_letters, 2))}{str(random.random())[2:6]}")
        db.session.add(pr)
    return True


def create_studio_session(studio_id: int, data: dict, add_members: list) -> bool:
    """
    Create new session in studio
    Assign studio members to the session
    """
    print(studio_id, data, add_members)
    if data.get("session_time"):
        data['session_time'] = datetime.strptime(data['session_time'], "%Y-%m-%dT%H:%M:%S")
    session_created = crud.create(StudioSession, {"created_by": g.user['id'], "studio_id": studio_id, "file_name": uuid.uuid1().hex, **data})
    session_created.external_meeting_id = f"{studio_id}#{session_created.id}#{uuid.uuid1().hex[:8]}#{''.join(i for i in data['name'].split())}"
    if add_members:
        add_members_to_session(add_members, session_created.id, studio_id)
    crud.create(StudioPresenter, {"session_id": session_created.id, "name": "ScreenRecorderBot",
                                  "email": "screenrecorderbot@abacies.com",
                                  "external_user_id": f"{str(random.random())[2:8]}#ScreenRecorderBot",
                                  "password": f"{''.join(i for i in random.sample(string.ascii_letters, 2))}"
                                              f"{str(random.random())[2:6]}"})
    return True


def edit_studio_session(session_id: int, data: dict, remove_members: list, add_members: list) -> bool:
    """
    Edit the studio session details.
    Remove members from the session
    Add new members to the session
    """
    ss = StudioSession.query.filter_by(id=session_id).first()
    if not ss:
        raise NoContent()
    if remove_members:
        for r in StudioSessionMember.query.filter_by(studio_session_id=session_id).filter(
                StudioSessionMember.user_id.in_(remove_members)).all():
            db.session.delete(r)
    if add_members:
        add_members_to_session(add_members, ss.id, ss.studio_id)
    if data:
        if data.get("session_time"):
            data['session_time'] = datetime.strptime(data['session_time'], "%Y-%m-%dT%H:%M:%S")
        crud.update(StudioSession, {"id": session_id}, data)
    else:
        crud.db_commit()
    return True


def delete_studio_session(studio_id: int) -> bool:
    crud.delete(StudioSession, {"id": studio_id})
    return True


def session_details_for_edit(studio_id: int, session_id: int, time_zone: str):
    if g.user['user_role'] == 1:
        ss = StudioSession.query.filter_by(id=session_id, studio_id=studio_id).first()
    else:
        ss = StudioSession.query.filter_by(id=session_id).join(Studio, StudioUserAssociation).filter(Studio.id == studio_id).filter(
            StudioUserAssociation.user_id == g.user['id']).first()
    if not ss:
        raise NoContent()
    data = dict(
        id=ss.id,
        name=ss.name,
        session_time=ss.session_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(time_zone)).strftime(
                "%Y-%m-%dT%H:%M:%S") if ss.session_time else None,
        state=ss.state,
        studio_id=ss.studio_id,
        is_active=ss.is_active,
        members=[{"id": m.id, "studio_user_id": m.studio_user_id, "name": m.user.name, 'user_id': m.user_id, 'user_role': m.user.user_role,
                 'email': m.user.email} for m in ss.members]
        )
    return data


def crud_session_presenters(session_id: int, data: dict) -> bool:
    """
    Remove and add new presenters
    """
    if data.get("remove_presenters"):
        for p in StudioPresenter.query.filter_by(session_id=session_id).filter(
                StudioPresenter.id.in_(data.get("remove_presenters"))).all():
            db.session.delete(p)
    for p in data.pop("add_presenters", []):
        pr = StudioPresenter(session_id=session_id, is_active=False, **p)
        db.session.add(pr)
    crud.db_commit()
    return True


def studio_session_call_presenter_validation(session_id: int, data: dict, ip_is: str) -> dict:
    # Chime first page itself will evaluate the login credentials and event expired or started
    pr_obj = StudioPresenter.query.filter_by(session_id=session_id, external_user_id=data['external_user_id']).join(
        StudioSession).filter(StudioSession.is_active == True).first()
    if not pr_obj:
        raise NoContent("This session has been deleted")
    if pr_obj.password != data['password']:
        raise BadRequest("Please enter the correct password and try again")
    pr_obj_session = pr_obj.session
    if pr_obj_session.state == "upcoming":
        raise BadRequest("This session has not started yet!..")
    if pr_obj_session.state == "closed":
        raise BadRequest("This session has been expired!...")
    crud.update(StudioPresenter, {"session_id": session_id, "external_user_id": pr_obj.external_user_id},
                {"ip_address": ip_is})
    if not pr_obj.session_user_assoc_id:
        return {"id": pr_obj.id, "name": pr_obj.name, "external_user_id": pr_obj.external_user_id, "recording": pr_obj_session.studio.recording,
                "session_name": pr_obj_session.name, "session_id": pr_obj.session_id,  "studio_id": pr_obj_session.studio_id, 
                "external_meeting_id": pr_obj_session.external_meeting_id, "user_role_id": 5}
    return {"id": pr_obj.id, "name": pr_obj.session_user_assoc.user.name, "external_user_id": pr_obj.external_user_id,
                "session_name": pr_obj_session.name, "session_id": pr_obj.session_id,  "studio_id": pr_obj_session.studio_id, 
                "external_meeting_id": pr_obj_session.external_meeting_id, "user_role_id": pr_obj.session_user_assoc.user.user_role}



# def get_studio_session_recordings(studio_id, session_id: int, time_zone: str):
#     if g.user['user_role'] != 1:
#         sm = StudioSessionMember.query.filter_by(studio_session_id=session_id, user_id=g.user['id']).first()
#         ss = sm.studio_session
#         if not sm:
#             raise Forbidden()
#     else:
#         ss = StudioSession.query.filter_by(id=session_id).first()
#     recordings = []
#     for p in StudioPresenter.query.filter_by(session_id=session_id).filter(StudioPresenter.session_user_assoc_id==None).all():
#         print(f"studio/{studio_id}/{session_id}/{p.external_user_id}.webm")
#         rec = generate_session_url(f"studio/{studio_id}/{session_id}/{p.external_user_id}.webm")
#         recordings.append({"id": p.id, "name": p.name, "url": rec})
#     if not recordings:
#         raise NoContent()
    
#     return {"id": ss.id, "name": ss.name, "created_by":{"id": ss.created_by, "name": ss.creator.name}, "recording_type": ss.studio.recording, 
#     "recordings": recordings,
#         "members": len([i for i in ss.members if i.user.user_role == 5]),"presenters": len([i for i in ss.presenters if i.email]), \
#             "created_at": ss.created.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(time_zone)).strftime("%Y-%m-%dT%H:%M:%S"),\
#                 "session_time": ss.session_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(time_zone)).strftime("%Y-%m-%dT%H:%M:%S") if ss.session_time else None}


def get_studio_session_recordings(studio_id, session_id: int, time_zone: str):
    if g.user['user_role'] != 1:
        sm = StudioSessionMember.query.filter_by(studio_session_id=session_id, user_id=g.user['id']).first()
        ss = sm.studio_session
        if not sm:
            raise Forbidden()
    else:
        ss = StudioSession.query.filter_by(id=session_id).first()
    recordings ={p.external_user_id: {"id": p.id, "name": p.name, "urls": []} for p in StudioPresenter.query.filter_by(session_id=session_id).filter(StudioPresenter.session_user_assoc_id==None).all()}
    s3 = resource_s3()
    my_bucket = s3.Bucket(Config.S3_MULTIMEDIA_BUCKET)
    print(recordings)
    for file_obj in my_bucket.objects.filter(Prefix=f"studio/{studio_id}/{session_id}/processed/"):
        key = file_obj.key
        rec = generate_session_url(key)
        print(key.split('/')[-1].split('_')[0])
        recordings[key.split('/')[-1].split('.')[0].replace('_', '#')]['urls'].append(rec)
    result = [k for k in recordings.values() if k.get('urls')]
    result.append({"id": 1, "name": "Screen Record", "urls": [generate_session_url(f"studio/{studio_id}/{session_id}/{ss.file_name}.mp4", Config.SESSION_RECORDER_BUCKET)]})
    if not recordings or not result:
        raise NoContent()
    return {"id": ss.id, "name": ss.name, "created_by":{"id": ss.created_by, "name": ss.creator.name}, "recording_type": ss.studio.recording, 
    "recordings": result,
        "members": len([i for i in ss.members if i.user.user_role == 5]),"presenters": len([i for i in ss.presenters if i.email]), \
            "created_at": ss.created.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(time_zone)).strftime("%Y-%m-%dT%H:%M:%S"),\
                "session_time": ss.session_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(time_zone)).strftime("%Y-%m-%dT%H:%M:%S") if ss.session_time else None}

def edit_studio_storage(studio_id: int, data: dict) -> bool:
    print(data)
    st = Studio.query.filter_by(id=studio_id).first()
    if g.user['user_role'] != 1:
        if st.created_by != g.user['id']:
            raise Forbidden()
    crud.update(Studio, {"id": studio_id}, {"storage_credential": json.dumps(data.pop("storage_credential", {})), **data})
    storage_credential, storage_details = json.loads(st.storage_credential), json.loads(st.storage_details)
    if storage_credential.get('access_token') and not storage_credential.get('error'):
        if st.storage_source == 3:
            drop_box = DropBox(storage_credential['access_token'])
            if not storage_details:
                drop_box.create_folder("worldStage/")
            elif storage_details.get('cus ot id'):
                result = drop_box.cusrsor_search_file_or_folders()
            else:
                pass

    return True


def get_studio_storage_cred(studio_id: int) -> dict:
    st = Studio.query.filter_by(id=studio_id).first()
    if g.user['user_role'] != 1:
        if st.created_by != g.user['id']:
            raise Forbidden()
    if st.storage_source in [2, 3]:
        data = {"storage_source": st.storage_source, "storage_credential": json.loads(st.storage_credential)}
        data.get("storage_credential", {}).pop('o_data', None)
        return data
    raise NoContent()