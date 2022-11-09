from re import M
from flask import jsonify, request, g
from flask.signals import request_started
from app.services.crud import CRUD
from app.api.user import tokenAuth
from app.models import Event, Presenter, Room, event
from app.services.auth import admin_user_authorizer
from app.services.recorder import stop_chime_screen_recording
from app.services.event_service import create_an_event, edit_an_event, delete_an_event, event_details_for_edit, get_proj_event_recordings
from app.services.custom_errors import *
from app.api import bp
from config import Config
from datetime import datetime
from app.services.multimedia import generate_session_url
from flask_socketio import SocketIO, emit, send
from app import socketio
import pytz
import json
import boto3
crud = CRUD()

@bp.route('/event/smijitj/<int:event_id>', methods=["GET"])
def smijith_dummy(event_id):
    data = {p.ndi_webrtc_instance: {"id": p.id, "name": p.name, "email": p.email, "private_ipv4": "", "ndi_webrtc_public_ip": p.ndi_webrtc_public_ip, "ndi_webrtc_instance": p.ndi_webrtc_instance, "ndi_webrtc_ec2_state": p.ndi_webrtc_ec2_state} for p in Presenter.query.filter_by(event_id=event_id).filter(Presenter.name != 'ScreenRecorderBot').all()}
    if data:
        print(data)
        client = boto3.client('ec2', aws_access_key_id="AKIAYZDEHMKLCPCPLZXM", aws_secret_access_key="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", region_name='us-east-1')
        response = client.describe_instances(InstanceIds =list(data.keys()))
        for res in response.get('Reservations', []):
            for ins in res.get('Instances', []):
                data[ins['InstanceId']]["private_ipv4"] = ins.get('PrivateIpAddress')
        print(data)
        return jsonify({"data": list(data.values()), "message": "Success"}), 200
    raise NoContent()


@bp.route('/event/create/<int:project_id>', methods=["POST"])
@tokenAuth.login_required
@admin_user_authorizer
def post_event(project_id):
    print(f"Event create {request.json}")
    # if g.user['user_role'] == 2:
    #     project_manager_validation(g.user['id'], project_id)
    #
    create_an_event(project_id, request.json, request.json.pop('add_rooms', []))
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/event/edit/<int:event_id>', methods=["PUT"])
@tokenAuth.login_required
@admin_user_authorizer
def put_event(event_id):
    print(f"event edit  {request.json}")
    # if g.user['user_role'] == 2:
    #     project_manager_validation(g.user['id'], request.json['project_id'])
    edit_an_event(request.json, event_id, request.json.pop("remove_rooms", []), request.json.pop("add_rooms", []),
                  request.json.pop("edit_rooms", []))
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/event/delete/<int:event_id>', methods=["DELETE"])
@tokenAuth.login_required
@admin_user_authorizer
def delete_event(event_id):
    # if g.user['user_role'] == 2:
    #     project_manager_validation(g.user['id'], request.args['project_id'])
    delete_an_event(event_id)
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/event/get/<int:event_id>', methods=["GET"])
@tokenAuth.login_required
@admin_user_authorizer
def get_an_event(event_id):
    # if g.user['user_role'] == 2:
    #     project_manager_validation(g.user['id'], request.args['project_id'])
    e = Event.query.filter_by(id=event_id).first()
    if e:
        data = {"id": e.id, "name": e.name, "event_time": e.event_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(
            request.args.get('time_zone'))).strftime("%Y-%m-%dT%H:%M:%S") if e.event_time else None, "project_id": e.project_id,
            "state": e.state, "created_by": e.created_by, "is_active": e.is_active, "rooms": {}, "users": {}, "room_order": [],
            "presenters": []}
        for r in e.rooms:
            data['rooms'][str(r.id)] = {"id": str(r.id), "name": r.name, "external_meeting_id": r.external_meeting_id,
                                        "members": []}
            data['room_order'].append(str(r.id))
            for m in r.room_members:
                data['rooms'][str(r.id)]['members'].append(str(m.user_id))
                if not data['users'].get(str(m.user_id)):
                    data['users'][str(m.user_id)] = {'id': str(m.id), 'user_id': str(m.user_id), 'name': m.user.name,
                                                     'user_role': m.user.user_role, 'email': m.user.email}
        now = datetime.utcnow()
        for p in e.presenters:
            if not p.proj_user_assoc_id:
                print(p.name)
                d = {'id': p.id, 'external_user_id': p.external_user_id, 'name': p.name, 'mic': p.mic,
                         'remote_audio_volume': p.remote_audio_volume, 'email': p.email,  'password': p.password,
                         'room_history': json.loads(p.room_history), 'current_room': json.loads(p.current_room),
                         'camera': p.camera, "user_role_id": 5}
                if p.avatar_file_name and (now - p.avatar_start_time).days>6:
                    p.avatar = generate_session_url(f"project/{e.project_id}/{event_id}/avatar/{p.avatar_file_name}")
                    p.avatar_start_time = now
                    crud.db_commit()
                d['avatar'] = p.avatar
            else:
                u = p.proj_assoc.user
                print(f"User {u}")
                d = {'id': p.id, 'external_user_id': p.external_user_id, 'name': u.name, 'mic': p.mic,
                         'remote_audio_volume': p.remote_audio_volume, 'email': u.email,  'password': p.password,
                         'room_history': json.loads(p.room_history), 'current_room': json.loads(p.current_room),
                         'camera': p.camera, "user_role_id": u.user_role}
                if u.avatar_file_name and (now - u.avatar_start_time).days >6:
                    u.avatar = generate_session_url(f"project/{e.project_id}/{event_id}/avatar/{p.avatar_file_name}")
                    u.avatar_start_time = now
                    crud.db_commit()
                d['avatar'] = u.avatar
            data['presenters'].append(d)

        return jsonify({"data": data, "message": "Success",
                        "status": 200}), 200
    raise NoContent()


@bp.route('/event/session_management/<int:event_id>', methods=["PUT"])
@tokenAuth.login_required
@admin_user_authorizer
def terminate_session(event_id):
    """
    After an event has been finished or event is running
    """
    print(request.json)
    if request.json.get("state") == "closed":
        for pr in Presenter.query.filter_by(event_id=event_id).filter(Presenter.current_room != json.dumps({})).all():
            socketio.emit("terminate meeting", request.json, room=f"room{pr.sid}")
            socketio.emit("terminate meeting", request.json, room=pr.sid)
        for r in Room.query.filter_by(event_id=event_id, terminated_recording=False).filter(Room.recording_task_id != None).all():
            sc = stop_chime_screen_recording(r.recording_task_id)
            if sc:
                crud.update(Room, {"id": r.id}, {"terminated_recording": True})
            print(f"***terminate-> {r.name}")
            id
    crud.update(Event, {"id": event_id}, request.json)
    return jsonify({"message": "Success", "status": 200}), 200



@bp.route('/event/get_for_edit/<int:project_id>/<int:event_id>', methods=["GET"])
@tokenAuth.login_required
def get_project_event_for_edit(project_id, event_id):
    data = event_details_for_edit(project_id, event_id, request.args.get('time_zone'))
    return jsonify({"data": data, "message": "Success", "status": 200}), 200



@bp.route('/project/event/recordings_dashboard/<int:proj_id>/<int:event_id>', methods=["GET"])
@tokenAuth.login_required
def project_event_recording(proj_id, event_id):
    """
    Generate recording URLS for studio session
    """
    data = get_proj_event_recordings(proj_id, event_id, request.args.get("time_zone"))
    return jsonify({"data": data, "message": "Success", "status": 200}), 200