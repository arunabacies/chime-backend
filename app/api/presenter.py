from app.models.studio import StudioSession
import re
from flask import jsonify, request, g, render_template, redirect
from sqlalchemy.orm import query, session
from app.models import event
from app.services.crud import CRUD
import json
from config import Config
from app.api.user import tokenAuth
from app.services.auth import admin_user_authorizer
from app.models.event import Event
from app.models import Presenter, StudioPresenter
from app.services.presenter import video_call_presenter_validation, update_presenter_network_info, event_presenter_live_data, get_event_presenter_details
from app.models.user import User
from app.services.custom_errors import *
from app.api import bp
from datetime import datetime
from app.services.sendgrid_email import send_email
from flask_socketio import SocketIO, emit, send
from app import create_app, socketio
from app.models.room import Room, RoomMember
from app import db
crud = CRUD()
import string
import random
from app.models.studio import StudioSession, Studio
import pytz
from app.services.recorder import start_chime_screen_recording, stop_chime_screen_recording, start_studio_screen_recording
from app.services.multimedia import add_presenters, remove_presenter


@bp.route('/event/create_update_presenter/<int:event_id>', methods=["POST"])
@tokenAuth.login_required
@admin_user_authorizer
def create_update_presenter(event_id):
    """
    Add new presenter to an event
    """
    data = request.json
    print(data)
    add_presenters_data, remove_presenters, edit_presenters = data.pop("add_presenters", []), data.pop("remove_presenters", []), data.pop("edit_presenters", [])
    event = Event.query.filter_by(id=event_id).first()
    if remove_presenters:
        remove_presenter(event.project_id, event_id, remove_presenters)
    if not Presenter.query.filter_by(event_id=event_id, name="ScreenRecorderBot").first():
        crud.create(Presenter, {"event_id": event_id, "mic": False, "camera": False, "name": "ScreenRecorderBot", "email": "screenrecorderbot@abacies.com", "external_user_id": f"{str(random.random())[2:8]}#ScreenRecorderBot", "password": f"{''.join(i for i in random.sample(string.ascii_letters, 2))}{str(random.random())[2:6]}"})
    event = Event.query.filter_by(id=event_id).first()
    if add_presenters_data:
        add_presenters(event.project_id, event_id, add_presenters_data)
    print(data)
    # if edit_presenters:
    #     edit_presenter_data(event.project_id, event_id, edit_presenters, [data.pop(f"edit_{i}", "") for i in len(edit_presenters)])
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/event/presenter_email_sent/<int:event_id>', methods=["POST"])
@tokenAuth.login_required
@admin_user_authorizer
def sent_email_to_presenter_login_cred(event_id):
    """
    Sent login credentials through email to the presenters of an event
    """
    all_data = []
    event = Event.query.filter_by(id=event_id).first()
    if not event:
        raise NoContent()
    for p in Presenter.query.filter_by(event_id=event_id).all():
        if not p.external_user_id or p.email == 'screenrecorderbot@abacies.com':
            continue
        link = f"{Config.MEETING_URL}?ExternalUserId={p.external_user_id}&EventId={event_id}&p={p.password}"
        if not p.proj_user_assoc_id:
            all_data.append({"name": p.name, "email": p.email, "link": link})
        else:
            all_data.append({"name": p.proj_assoc.user.name, "email": p.proj_assoc.user.email, "link": link})
        call_join_template = render_template("presenter_invitation.html", link=link, name=all_data[-1]['name'], event_name=event.name)
        send_email(to_email=all_data[-1]['email'], html_content=call_join_template, subject=f"Invitation to join call at session {event.name}")
    to_emails = [u.email for u in User.query.filter_by(user_role=1).all()]
    call_join_template = render_template("call_links_email.html", event_name=event.name, all_data=all_data)
    send_email(to_email=to_emails, html_content=call_join_template, subject=f"Invitation to join call at session {event.name}")
    return jsonify({"message": "Success", "status": 200}), 200


@socketio.on("joined room")
def update_presenter_join_room(data):
    print("****(joined room")
    print(f"Joined room {data}")
    print(f"new socket is {request.sid}")
    """
    When a presenter/any user joined a room then update the database current room & previous room history
    """
    presenter_obj = Presenter.query.filter_by(external_user_id=request.args.get('external_user_id')).first()
    if not presenter_obj:
        raise NoContent()
    if len(json.loads(presenter_obj.current_room))>0:
        presenter_obj.room_history = json.dumps(json.loads(presenter_obj.room_history) +
                                                [json.loads(presenter_obj.current_room)])
    presenter_obj.current_room = json.dumps(
        {"name": data.get("room_name") , "joined_at": datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")})
    presenter_obj.mic = data['mic']
    presenter_obj.camera = data['camera']
    room = Room.query.filter_by(event_id=data['event_id'], name=data['room_name']).first()
    active_members = set(json.loads(room.active_members) + [presenter_obj.id])
    room.active_members = json.dumps(list(active_members))
    crud.db_commit()
    latest_data = event_presenter_live_data(presenter_obj.event_id)
    if ((room.name != 'Waiting Room' and not room.recording_task_id) and room.project.recording):
        # chime screen recording api
        print("**chime screen recording api******", data['room_name'])
        room.recording_task_id = start_chime_screen_recording(room.event_id, room.id, room.session_record_file)
        print(f"***CHime recorder started task id is {room.recording_task_id}")
        crud.db_commit()
        for del_rm in Room.query.filter_by(event_id=data['event_id'],terminated_recording=False).filter(Room.recording_task_id != None).all():
            if len(json.loads(del_rm.active_members)) <= 1:
                sc = stop_chime_screen_recording(del_rm.recording_task_id)
                if sc:
                    crud.update(Room, {"id": del_rm.id}, {"terminated_recording": True})
    emit("event latest data", {"data": latest_data}, room=f"{data['event_id']}_room") # transfer data to react app
    return True

@socketio.on("joined meeting")
def update_studio_presenter_joined(data):
    """
    When a presenter/any user in the Studio joined in the meeting then update the database 
    """
    print(f"**Joined MEETING {data}")
    print(request.args)
    sp = StudioPresenter.query.filter_by(session_id=data.get('session_id'), external_user_id=data.get('external_user_id')).first()
    sp.is_active = True
    if sp.session.studio.recording and sp.session.start_recording:
        if not sp.session.recording_task_id:
            sp.session.recording_task_id = start_studio_screen_recording(data['session_id'], sp.session.file_name)
        socketio.emit("start recording", {"external_user_id": sp.external_user_id, "session_id": sp.session_id}, room=f"room{sp.sid}")
        socketio.emit("start recording", {"external_user_id": sp.external_user_id, "session_id": sp.session_id}, room=sp.sid)
    crud.db_commit()
    return True

@socketio.on("left meeting")
def studio_presenter_left_meeting(data):
    """
    Update the database when a studio presenter left an meeting
    """
    print(f"Left meeting: {request.args}")
    print(data)
    crud.update(StudioPresenter, {"external_user_id": data.get('external_user_id'), "session_id": data.get('session_id')}, {"is_active": False})   
    return True


@socketio.on("disconnect")
def presenter_disconnected():
    """
    When call is disconneted update table
    """
    print(f"DISCONNECT***: {request.args}")
    print(f"SOCKET Id is {request.sid}")
    presenter_obj = None
    if request.args.get('event_id'):
        if request.args.get('external_user_id'):
            presenter_obj = Presenter.query.filter_by(external_user_id=request.args['external_user_id']).first()
        else: 
            presenter_obj = Presenter.query.filter_by(sid=request.sid).first()
    elif request.args.get('session_id'):
        if request.args.get('external_user_id'):
            presenter_obj = StudioPresenter.query.filter_by(external_user_id=request.args['external_user_id']).first() 
        else:
            presenter_obj = StudioPresenter.query.filter_by(sid=request.sid).first()
            if presenter_obj.started_recording:
                socketio.emit("stop recording", {"external_user_id": presenter_obj.external_user_id, "session_id": presenter_obj.session_id}, room=f"room{presenter_obj.sid}")
                socketio.emit("stop recording", {"external_user_id": presenter_obj.external_user_id, "session_id": presenter_obj.session_id}, room=presenter_obj.sid)
        if not presenter_obj:
            return False
        presenter_obj.is_active = False
        crud.db_commit()
        return True
    if not presenter_obj:
        return False
    room_name = ""
    print(f"Current room is: {presenter_obj.current_room}")
    if len(json.loads(presenter_obj.current_room))>0:
        print("____length current room")
        room_name = json.loads(presenter_obj.current_room).get('name')
        print(room_name)
        presenter_obj.room_history = json.dumps(json.loads(presenter_obj.room_history) +[json.loads(presenter_obj.current_room)])
    presenter_obj.current_room = json.dumps({})
    if not room_name:
        return True
    if room_name != "Waiting Room":
        room = Room.query.filter_by(event_id=presenter_obj.event_id, name=room_name).first()
        print(room)
        print(room.active_members)
        active_members = json.loads(room.active_members)
        try:
            active_members.remove(presenter_obj.id)
        except:
            pass
        print(room.active_members)
        room.active_members = json.dumps(active_members)
        if room.recording_task_id and len(active_members) <= 1:
            print(f"**Discooneect Stoppinng {room.recording_task_id}")
            sc = stop_chime_screen_recording(room.recording_task_id)
            if sc:
                room.terminated_recording = True
            room.rec_status = True
        crud.db_commit()
    latest_data = event_presenter_live_data(presenter_obj.event_id)
    emit("event latest data", {"data": latest_data}, room=f"{presenter_obj.event_id}_room") # transfer data to react app
    return True



@bp.route('/event/presenter/authentication_checker/<int:event_id>', methods=["POST"])
def presenter_validating_video_call_url_auth(event_id):
    """
    Presenter have to enter the password initially to get start the video call
    """
    print(f"input {request.json}")
    ip_is = request.headers.get("X-Forwarded-For") if request.headers.get("X-Forwarded-For") else request.remote_addr
    data = video_call_presenter_validation(event_id, request.json, ip_is)
    return jsonify({"data": data, "message": "Success", "status": 200}), 200


@bp.route('/event/switch_room/<int:event_id>', methods=["POST"])
@tokenAuth.login_required
def switch_room_req(event_id):
    """
    Admin or crew members switch the control room of a presenter
    """
    print(request.json)
    pr = Presenter.query.filter_by(external_user_id=request.json.get('external_user_id'), event_id=event_id).first()
    if pr.sid:
        if pr.proj_user_assoc_id:
            r = Room.query.filter_by(event_id=event_id, name=request.json.get('change_room_to')).join(RoomMember).filter(RoomMember.proj_user_id==pr.proj_user_assoc_id).first()
        else:
            r = Room.query.filter_by(event_id=event_id, name=request.json.get('change_room_to')).first()
            print(r)
        if r:
            socketio.emit("switch room", {"event_id": event_id, "external_meeting_id": r.external_meeting_id, "mic": pr.mic,
                                          "current_room": json.loads(pr.current_room).get("name"), "camera": pr.camera,
                                          "event_name": pr.event.name, "user_name": pr.name or pr.proj_assoc.user.name,
                                          "remote_audio_volume": pr.remote_audio_volume, "broadcast_ndi": r.broadcast_ndi,
                                            **request.json}, room=pr.sid)
            socketio.emit("switch room", {"event_id": event_id, "external_meeting_id": r.external_meeting_id, "mic": pr.mic,
                                          "current_room": json.loads(pr.current_room).get("name"), "camera": pr.camera,
                                          "event_name": pr.event.name, "user_name": pr.name or pr.proj_assoc.user.name,
                                          "remote_audio_volume": pr.remote_audio_volume, "broadcast_ndi": r.broadcast_ndi, 
                                          **request.json}, room=f"room{pr.sid}")
            return jsonify({"message": "Success", "status": 200}), 200
        raise BadRequest(f"{pr.name or pr.proj_assoc.user.name} is not a member of {request.json.get('change_room_to')}")
    raise NoContent()


@bp.route('/event/audio_video_post/<int:event_id>', methods=["POST"])
@tokenAuth.login_required
def audio_video_admin_post(event_id):
    """
    Admin/crew can mute/unmute or disable/enable camera of an presenter
    """
    print(request.json)
    pr = Presenter.query.filter_by(external_user_id=request.json.get('external_user_id'), event_id=event_id).first()
    if request.json.get('change_mic_state'):
        # socketio.emit("switch mic state", {"change_mic_state": request.json.get("change_mic_state")}, room=f"room{pr.sid}")
        socketio.emit("switch mic state", {"change_mic_state": request.json.get("change_mic_state")}, room=pr.sid)
    elif request.json.get('change_video_state'):
        # socketio.emit("switch video camera state", {"video_camera_state": request.json.get('change_video_state')}, room=f"room{pr.sid}")
        socketio.emit("switch video camera state", {"video_camera_state": request.json.get('change_video_state')}, room=pr.sid)
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/event/remote_audio_volume_change/<int:event_id>', methods=["PUT"])
@tokenAuth.login_required
def remote_audio_volume_req(event_id):
    """
    Presenter current state of mic and camera
    """
    print(request.json)
    pr = Presenter.query.filter_by(event_id=event_id, external_user_id=request.json['external_user_id']).first()
    if pr:
        socketio.emit("set remote volume", request.json, room=f"room{pr.sid}")
        socketio.emit("set remote volume", request.json, room=pr.sid)
        return jsonify({"message": "Success", "status": 200}), 200
    raise NoContent()


@socketio.on("current device state")
def update_presenter_device_state(data):
    """
    Update mic/video state and remote volume
    """
    print(f" current device state: {data}")
    p_obj = Presenter.query.filter_by(external_user_id=request.args.get('external_user_id')).first()
    crud.update(Presenter, {"external_user_id": request.args.get('external_user_id')}, data)
    latest_data = event_presenter_live_data(p_obj.event_id)
    emit("device notification", {"id": p_obj.id, "name": p_obj.name or p_obj.proj_assoc.user.name, **data}, room=f"{p_obj.event_id}_room") # transfer data to react app
    emit("event latest data", {"data": latest_data}, room=f"{p_obj.event_id}_room") # transfer data to react app
    return True


@bp.route('/event/remote_user_network_info/<int:event_id>', methods=["PUT"])
@tokenAuth.login_required
def req_remote_user_network_info(event_id):
    """
    Admin/crew requests to view the network info of an presenter
    """
    print(request.json)
    pr = Presenter.query.filter_by(event_id=event_id, external_user_id=request.json['external_user_id']).first()
    if pr:
        socketio.emit("get network info", room=f"room{pr.sid}")
        socketio.emit("get network info", room=pr.sid)
        return jsonify({"message": "Success", "status": 200}), 200
    raise NoContent()


@socketio.on("current network info")
def update_current_network_info(data):
    """
    Update system specific network info
    """
    print(data)
    print(request.args)
    p_obj = Presenter.query.filter_by(external_user_id=request.args.get('external_user_id')).first()
    update_presenter_network_info(request.args.get('external_user_id'), data)    
    latest_data = event_presenter_live_data(p_obj.event_id)
    emit("event latest data", {"data": latest_data}, room=f"{p_obj.event_id}_room") # transfer data to react 
    return True

@bp.route('/event/remote_user_network_info/<int:event_id>', methods=["GET"])
@tokenAuth.login_required
def get_remote_user_network_info(event_id):
    """
    Get specific user system network info
    """
    data = Presenter.query.filter_by(event_id=event_id, external_user_id=request.args.get('external_user_id')).first()
    print(json.loads(data.network_info))
    data = Presenter.query.filter_by(event_id=event_id, external_user_id=request.args.get('external_user_id')).first()
    if data:
        return jsonify({"data": {"network_info": json.loads(data.network_info), "ip_address": data.ip_address}, "message": "Success", "status": 200}), 200
    raise NoContent()

@socketio.on("remote volume change")
def update_volume(data):
    """
    Update Remote volume
    """
    print(data)
    print(request.args)
    p_obj = Presenter.query.filter_by(external_user_id=request.args.get('external_user_id')).first()
    crud.update(Presenter, {"external_user_id": request.args.get('external_user_id')}, {"remote_audio_volume": data.get("volume")})
    latest_data = event_presenter_live_data(p_obj.event_id)
    emit("event latest data", {"data": latest_data}, room=f"{p_obj.event_id}_room") # transfer data to react 
    return True


@bp.route('/event/presenter_data_for_edit/<int:project_id>/<int:event_id>', methods=["GET"])
@tokenAuth.login_required
def get_presenter_data_for_edit(project_id, event_id):
    data = get_event_presenter_details(project_id, event_id)
    return jsonify({"data": data, "message": "Success", "status": 200}), 200
