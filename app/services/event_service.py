from app.services.crud import CRUD
from datetime import datetime
from flask import g
from app.services.custom_errors import *
from app.models import Event, Room, RoomMember, ProjectUserAssociation, Presenter, Project, event
from app import db
from app.services.multimedia import resource_s3, generate_session_url
import re
import uuid
import json
from config import Config
from datetime import datetime
import string
import pytz
import random
crud = CRUD()


def create_an_event(project_id: int, data: dict, add_rooms: list) -> bool:
    print(project_id, data, add_rooms)
    if data.get("event_time"):
        data['event_time'] = datetime.strptime(data['event_time'], "%Y-%m-%dT%H:%M:%S")
    # if data.get("control_rooms"):
    #     data['control_rooms'] = json.dumps(data['control_rooms'])
    ev_created = crud.create(Event, {"created_by": g.user['id'], "project_id": project_id, **data})
    users = set()
    for r in add_rooms:
        print(r)
        created = crud.create(Room, {"name": r['name'], "event_id": ev_created.id, "proj_id": project_id,
                                     "broadcast_ndi": r['broadcast_ndi'], "external_meeting_id":
                                         f"{project_id}#{ev_created.id}#{uuid.uuid1().hex[:8]}#"
                                         f"{''.join(i for i in r['name'].split())}", "session_record_file": f"{r['name'].replace(' ','-')}{uuid.uuid1().hex}" if ev_created.project.recording else ""})
        for u in r.get("add_members", []):
            rm = RoomMember(room_id=created.id,  **u)
            db.session.add(rm)
            if u.get('proj_user_id') not in  users:
                pa = ProjectUserAssociation.query.filter_by(id=u.get('proj_user_id')).first()
                pr = Presenter(event_id=ev_created.id, proj_user_assoc_id=u.get('proj_user_id'), external_user_id=f"{str(random.random())[2:8]}#{pa.user.name.split()[0]}", password=f"{''.join(i for i in random.sample(string.ascii_letters, 2))}{str(random.random())[2:6]}")
                print(pr)
                users.add(u.get('proj_user_id'))
                db.session.add(pr)
                print(f"pr added {u}")
    crud.db_commit()
    return True


def edit_an_event(data: dict, event_id: int, remove_rooms: list, add_rooms: list, edit_rooms: list) -> bool:
    event = Event.query.filter_by(id=event_id).first()
    if not event:
        raise NoContent()
    if remove_rooms:
        for r in Room.query.filter_by(event_id=event_id).filter(Room.id.in_(remove_rooms)).all():
            db.session.delete(r)
        crud.db_commit()
    if edit_rooms:
        for r in edit_rooms:
            id_ = r.pop('id')
            if r.get("remove_members", []):
                for u in RoomMember.query.filter_by(room_id=id_).filter(RoomMember.user_id.in_(
                        r.pop("remove_members"))).all():
                    db.session.delete(u)
                crud.db_commit()
            r.pop("remove_members", None)
            for u in r.pop("add_members", []):
                print(u)
                crud.create_or_update(RoomMember, {"room_id": id_, "user_id": u['user_id']}, {"room_id": id_, **u})
                if not Presenter.query.filter_by(event_id=event_id, proj_user_assoc_id=u.get('proj_user_id')).first():
                    pa = ProjectUserAssociation.query.filter_by(id=u.get('proj_user_id'), project_id=event.project_id).first()
                    pr = Presenter(event_id=event_id, proj_user_assoc_id=u.get('proj_user_id'), external_user_id=f"{str(random.random())[2:8]}#{pa.user.name.split()[0]}", password=f"{''.join(i for i in random.sample(string.ascii_letters, 2))}{str(random.random())[2:6]}")
                    print(pr)
                    db.session.add(pr)
            crud.db_commit()
            if r:
                crud.update(Room, {"id": id_}, r)
    for r in add_rooms:
        created = crud.create(Room, {"name": r['name'], "event_id": event_id, "proj_id": event.project_id,
                                     "broadcast_ndi": r['broadcast_ndi'], "external_meeting_id": f"{event.project_id}#{event.id}#{uuid.uuid1().hex[:8]}#{''.join(i for i in r['name'].split())}", "session_record_file": f"{r['name'].replace(' ','-')}{uuid.uuid1().hex}" if event.project.recording else ""})
        for u in r.get("add_members", []):
            crud.create(RoomMember, {"room_id": created.id, **u})
            if not Presenter.query.filter_by(event_id=event_id, proj_user_assoc_id=u.get('proj_user_id')).first():
                    pa = ProjectUserAssociation.query.filter_by(id=u.get('proj_user_id'), project_id=event.project_id).first()
                    pr = Presenter(event_id=event_id, proj_user_assoc_id=u.get('proj_user_id'), external_user_id=f"{str(random.random())[2:8]}#{pa.user.name.split()[0]}", password=f"{''.join(i for i in random.sample(string.ascii_letters, 2))}{str(random.random())[2:6]}")
                    print(pr)
                    db.session.add(pr)
        crud.db_commit()            
    if data:
        if data.get("event_time"):
            data['event_time'] = datetime.strptime(data['event_time'], "%Y-%m-%dT%H:%M:%S")
        if data.get("control_rooms"):
            data['control_rooms'] = json.dumps(data['control_rooms'])
        crud.update(Event, {"id": event_id}, data)
    return True


def delete_an_event(event_id: int) -> bool:
    crud.delete(Event, {"id": event_id})
    return True

def event_details_for_edit(project_id: int, event_id, time_zone: str):
    if g.user['user_role'] == 1:
        e = Event.query.filter_by(id=event_id, project_id=project_id).first()
    else:
        e = Event.query.filter_by(id=event_id).join(Project, ProjectUserAssociation).filter(Project.id == project_id).filter(
            ProjectUserAssociation.user_id == g.user['user_id']).first()
    if not e:
        raise NoContent()
    data = dict(
        id=e.id,
        name=e.name,
        event_time=e.event_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(time_zone)).strftime(
                "%Y-%m-%dT%H:%M:%S") if e.event_time else None,
        state=e.state,
        project_id=e.project_id,
        is_active=e.is_active,
        rooms=[{"id": r.id, "name": r.name, "broadcast_ndi": r.broadcast_ndi,"members": [
                {'id': m.id, 'user_id': m.user_id, 'name': m.user.name, 'user_role': m.user.user_role,
                 'email': m.user.email} for m in r.room_members]} for r in e.rooms]
        )
    return data


def get_proj_event_recordings(proj_id, event_id: int, time_zone: str):
    if g.user['user_role'] != 1:
        room = Room.query.filter_by(event_id=event_id).join(RoomMember).filter(RoomMember.user_id==g.user['id']).first()
        event = room.event
    else:
        event = Event.query.filter_by(id=event_id).first()
    if not event:
        raise Forbidden()
    recordings ={p.external_user_id: {"id": p.id, "name": p.name, "urls": []} for p in Presenter.query.filter_by(event_id=event_id).filter(Presenter.proj_user_assoc_id==None).all()}
    s3 = resource_s3()
    my_bucket = s3.Bucket(Config.S3_MULTIMEDIA_BUCKET)
    print(recordings)
    for file_obj in my_bucket.objects.filter(Prefix=f"project/{proj_id}/{event_id}/"):
        key = file_obj.key
        if "/avatar/" in key:
            continue
        rec = generate_session_url(key)
        print(key.split('/')[-1].split('-')[0])
        recordings[key.split('/')[-1].split('-')[0]]['urls'].append(rec)
    result = [k for k in recordings.values() if k.get('urls')]
    my_bucket = s3.Bucket(Config.SESSION_RECORDER_BUCKET)
    result.append({"id": 1, "name": "Screen Record", "urls": []}) 
    for file_obj in my_bucket.objects.filter(Prefix=f"project/{proj_id}/{event_id}/"):
        key = file_obj.key
        rec = generate_session_url(key, Config.SESSION_RECORDER_BUCKET)
        print(key.split('/')[-1].split('-')[0])
        result[-1]['urls'].append(rec)
    if not recordings or not result:
        raise NoContent()
    return {"id": event.id, "name": event.name, "created_by":{"id": event.created_by, "name": event.creator.name},
    "recordings": result,
        "members": len(set(m.user_id for r in event.rooms for m in r.room_members)),"presenters": len([i for i in event.presenters if i.name != "ScreenRecorderBot"  and not i.proj_user_assoc_id]), \
            "created_at": event.created.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(time_zone)).strftime("%Y-%m-%dT%H:%M:%S"),\
                "session_time": event.event_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(time_zone)).strftime("%Y-%m-%dT%H:%M:%S") if event.event_time else None}