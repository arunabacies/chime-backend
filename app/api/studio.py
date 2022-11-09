from flask import json, jsonify, request, g, render_template
from sqlalchemy.orm import session
from app.models.studio import Studio, StudioPresenter, StudioSession, StudioUserAssociation, StudioSessionMember
from app.services.crud import *
from app.api.user import tokenAuth
from app.services.auth import admin_user_authorizer
from app.models.user import User
from app.services.recorder import stop_chime_screen_recording
from app.services.studio import create_studio, edit_studio, list_studios, edit_studio_session, create_studio_session, \
    session_details_for_edit, single_studio, studio_session_call_presenter_validation, crud_session_presenters, \
    delete_studio_session, get_studio_session_recordings, edit_studio_storage, get_studio_storage_cred
from app.services.recorder import start_studio_screen_recording
from app.api import bp
from flask_socketio import SocketIO, emit, send
from app.services.sendgrid_email import send_email
from app import socketio
from config import Config
import requests
from sqlalchemy import or_
crud = CRUD()


@bp.route('/studio/add', methods=["POST"])
@tokenAuth.login_required
@admin_user_authorizer
def post_studio():
    print(f"Post Studio: {request.json}")
    create_studio(request.json, request.json.pop("add_users", []))
    return jsonify({"message": "Success", "status": 200}), 200

@bp.route('/studio/storage_cred/<int:studio_id>', methods=["PUT"])
@tokenAuth.login_required
def edit_storage_cred(studio_id):
    edit_studio_storage(studio_id, request.json)
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/studio/storage_cred/<int:studio_id>', methods=["GET"])
@tokenAuth.login_required
def get_storage_cred(studio_id):
    data = get_studio_storage_cred(studio_id)
    return jsonify({"data": data, "message": "Success", "status": 200}), 200


@bp.route('/studio/edit/<int:studio_id>', methods=["PUT"])
@tokenAuth.login_required
@admin_user_authorizer
def put_studio(studio_id):
    print(f"Put studio: {request.json}")
    # if g.user['user_role'] == 2:
    #     project_manager_validation(g.user['id'], project_id)
    edit_studio(request.json, studio_id, request.json.pop("remove_users", []), request.json.pop("add_users", []))
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/studio/delete/<int:studio_id>', methods=["DELETE"])
@tokenAuth.login_required
@admin_user_authorizer
def delete_studio(studio_id):
    # if g.user['user_role'] == 2:
    #     project_manager_validation(g.user['id'], project_id)
    crud.delete(Studio, {"id": studio_id})
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/studio/list', methods=["GET"])
@tokenAuth.login_required
def get_studio_list():
    data = list_studios(request.args['time_zone'], int(request.args.get("page", 1)), int(request.args.get("per_page", 6)))
    return jsonify({"data": data[0], "message": "Success", "status": 200, "pagination": data[1]}), 200


@bp.route('/studio/get_single_studio/<int:studio_id>', methods=["GET"])
@tokenAuth.login_required
def get_single_studio(studio_id):
    print(f"Get single Studio : {request.args}")
    result = single_studio(request.args['time_zone'], studio_id)
    print(result)
    return jsonify({"data": result, "message": "Success", "status": 200}), 200


@bp.route('/studio/user/<int:studio_id>', methods=["DELETE"])
@tokenAuth.login_required
@admin_user_authorizer
def delete_user_from_studio(studio_id):
    print(request.args)
    if g.user['user_id'] == request.args.get('user_id'):
        raise UnProcessable("Sorry you cannot delete yourself")
    crud.delete(StudioUserAssociation, {"studio_id": studio_id, "user_id": request.args.get('user_id')})
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/session/create/<int:studio_id>', methods=["POST"])
@tokenAuth.login_required
@admin_user_authorizer
def post_studio_session(studio_id):
    print(f"Studio session create {request.json}")
    # if g.user['user_role'] == 2:
    #     project_manager_validation(g.user['id'], project_id)
    #
    create_studio_session(studio_id, request.json, request.json.pop('add_members', []))
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/session/edit/<int:session_id>', methods=["PUT"])
@tokenAuth.login_required
@admin_user_authorizer
def put_studio_session(session_id):
    print(f"Studio session edit  {request.json}")
    # if g.user['user_role'] == 2:
    #     project_manager_validation(g.user['id'], request.json['project_id'])
    edit_studio_session(session_id, request.json, request.json.pop("remove_members", []), request.json.pop("add_members", []))
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/session/delete/<int:session_id>', methods=["DELETE"])
@tokenAuth.login_required
@admin_user_authorizer
def studio_session_delete(session_id):
    # if g.user['user_role'] == 2:
    #     project_manager_validation(g.user['id'], request.args['project_id'])
    delete_studio_session(session_id)
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/session/get_for_edit/<int:studio_id>/<int:session_id>', methods=["GET"])
@tokenAuth.login_required
def get_studio_session_det_for_edit(studio_id, session_id):
    data = session_details_for_edit(studio_id, session_id, request.args.get('time_zone'))
    return jsonify({"data": data, "message": "Success", "status": 200}), 200


@bp.route('/session/session_management/<int:session_id>', methods=["PUT"])
@tokenAuth.login_required
@admin_user_authorizer
def terminate_studio_session(session_id):
    """
    After an event has been finished or event is running
    """
    print(request.json)
    if request.json.get("state") == "closed":
        external_ids = []
        for pr in StudioPresenter.query.filter_by(session_id=session_id).filter(StudioPresenter.sid != None).all():
            if not pr.session_user_assoc_id or pr.name == "ScreenRecorderBot":
                external_ids.append(pr.external_user_id)
            socketio.emit("terminate meeting", request.json, room=f"room{pr.sid}")
            socketio.emit("terminate meeting", request.json, room=pr.sid)
            rr = requests.post("https://4k.digitaloasis.solutions/api/process/video", headers={'Content-type': 'application/json'}, data=json.dumps({"session_id": session_id, "studio_id": pr.session.studio_id, "externalUserIds": external_ids}))           
        stop_chime_screen_recording(pr.session.recording_task_id)
        StudioPresenter.query.filter_by(session_id=session_id).filter(or_(StudioPresenter.session_user_assoc_id != None,
                                         StudioPresenter.name == 'ScreenRecorderBot')).delete()
        r = requests.post(f"{Config.RECORDER_BACKEND_STUDIO_API}/recordings/terminate", headers={'Content-Type': 'application/json'}, data=json.dumps({"ExternalUserIds": external_ids, "session_id": session_id, "studio_id": pr.session.studio_id}))
        print(r)
    crud.update(StudioSession, {"id": session_id}, request.json)
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/session/create_update_presenter/<int:session_id>', methods=["POST"])
@tokenAuth.login_required
@admin_user_authorizer
def create_update_studio_session_presenter(session_id):
    """
    Add new presenter to studio session
    No edit operation. if edited then remove it and add it as new presenter
    """
    data = request.json
    print(data)
    crud_session_presenters(session_id, request.json)
    return jsonify({"message": "Success", "status": 200}), 200

@bp.route('/session/presenter_email_sent/<int:session_id>', methods=["POST"])
@tokenAuth.login_required
@admin_user_authorizer
def sent_email_to_session_presenter(session_id):
    #Sent login credentials through email to the presenters of an event
    all_data = []
    for p in StudioPresenter.query.filter_by(session_id=session_id).filter(StudioPresenter.email != None, StudioPresenter.name != 'ScreenRecorderBot').all():
        link = f"{Config.STUDIO_MEETING_URL}?ExternalUserId={p.external_user_id}&StudioSessionId={session_id}&p={p.password}"
        all_data.append({"name": p.name, "email": p.email, "link": link})
        call_join_template = render_template("presenter_invitation.html", link=link, name=all_data[-1]['name'], event_name=p.session.name)
        send_email(to_email=p.email, html_content=call_join_template, subject=f"Invitation to join call at session {p.session.name}")
    to_emails = [u.email for u in User.query.filter_by(user_role=1).all()]
    call_join_template = render_template("call_links_email.html", event_name=p.session.name, all_data=all_data)
    send_email(to_email=to_emails, html_content=call_join_template, subject=f"Invitation to join call at session {p.session.name}")
    return jsonify({"message": "Success", "status": 200}), 200

@bp.route("/session/presenter_data_for_edit/<int:studio_id>/<int:session_id>", methods=["GET"])
@tokenAuth.login_required
def session_presenter_list(studio_id, session_id):
    """
    List all presenters in an session
    """
    data = [{"id": m.id, "name": m.name, "email": m.email, "external_user_id": m.external_user_id, "password": m.password} \
        for m in StudioPresenter.query.filter_by(session_id=session_id, session_user_assoc_id=None).filter(StudioPresenter.name != 'ScreenRecorderBot').all()]
    return jsonify({"data": data, "message": "Success", "status": 200}), 200

@bp.route("/session/meeting_redirect/<int:session_id>", methods=["GET"])
@tokenAuth.login_required
def session_meeting_redirect(session_id):
    pr = StudioPresenter.query.filter_by(session_id=session_id).join(StudioSessionMember).filter(StudioSessionMember.user_id==g.user['id']).first()
    print(pr)
    print(StudioPresenter.query.filter_by(session_id=session_id).all())
    if not pr:
        raise Forbidden("You are not the crew member of this session")
    print({"data": {"url": f"{Config.STUDIO_MEETING_URL}?ExternalUserId={pr.external_user_id}&StudioSessionId={pr.session_id}&p={pr.password}"}, "message": "Success", "status": 200})
    return jsonify({"data": {"url": f"{Config.STUDIO_MEETING_URL}?ExternalUserId={pr.external_user_id}&StudioSessionId={pr.session_id}&p={pr.password}"}, "message": "Success", "status": 200}), 200
    # return redirect(f"{Config.STUDIO_MEETING_URL}?ExternalUserId={pr.external_user_id}&StudioSessionId={pr.session_id}&p={pr.password}", code=302)

@bp.route('/session/presenter/authentication_checker/<int:session_id>', methods=["POST"])
def studio_session_meeting_val(session_id):
    #Presenter have to enter the password initially to get start the video call
    print(f"input {request.json}")
    ip_is = request.headers.get("X-Forwarded-For") if request.headers.get("X-Forwarded-For") else request.remote_addr
    data = studio_session_call_presenter_validation(session_id, request.json, ip_is)
    return jsonify({"data": data, "message": "Success", "status": 200}), 200

@bp.route("/session/recording/<int:studio_id>/<int:session_id>", methods=["POST"])
@tokenAuth.login_required
def session_record(studio_id, session_id):
    p = None
    if request.args.get("state") == "start":
        crud.update(StudioSession, {"id": session_id}, {"start_recording":  True})
        print(StudioPresenter.query.filter_by(session_id=session_id, started_recording=False, session_user_assoc_id=None).filter(StudioPresenter.sid != None).all())
        for p in StudioPresenter.query.filter_by(session_id=session_id, started_recording=False, session_user_assoc_id=None).filter(StudioPresenter.sid != None).all():
            print(f"---> Start recording req: {p}")
            if p.sid:
                socketio.emit("start recording", {"external_user_id": p.external_user_id, "session_id": p.session_id}, room=f"room{p.sid}")
                socketio.emit("start recording", {"external_user_id": p.external_user_id, "session_id": p.session_id}, room=p.sid)
        try:
            if p and p.session.studio.recording and p.session.start_recording and not p.session.recording_task_id:
                print("/session/recording/**** start recorder requesting")
                p.session.recording_task_id = start_studio_screen_recording(session_id, p.session.file_name)
                crud.db_commit()
        except Exception as e:
            print(f"Exception as e: {e}")
        return jsonify({"message": "Success", "status": 200}), 200
    if request.args.get("state") == "stop":
        for p in StudioPresenter.query.filter_by(session_id=session_id, started_recording=True, stopped_recording=False, is_active=True, session_user_assoc_id=None).all():
            print(f"-->Stop recording: {p}")
            socketio.emit("stop recording", {"external_user_id": p.external_user_id, "session_id": p.session_id}, room=f"room{p.sid}")
            socketio.emit("stop recording", {"external_user_id": p.external_user_id, "session_id": p.session_id}, room=p.sid)
        try:
            stop_chime_screen_recording(p.session.recording_task_id)
        except Exception as e:
            print(str(e))
        return jsonify({"message": "Success", "status": 200}), 200
    raise UnProcessable(f"Not able to {request.args['state']}recording")

@socketio.on('started recording')
def started_studio_recording(data):
    """Sent from chime if recrding gets started."""
    print(f"******************recording started****************** {data}")
    sr = StudioPresenter.query.filter_by(external_user_id=data['external_user_id'], session_id=data["session_id"]).first()
    sr.started_recording = True
    sr.stored = True
    if not sr.session.start_recording:
        sr.session.start_recording = True
    crud.db_commit()
    return True

@socketio.on('stopped recording')
def stopped_studio_recording(data):
    """Sent from chime if recrding gets stopped."""
    print(f"******************recording stopped****************** {data}")
    sr = StudioPresenter.query.filter_by(external_user_id=data['external_user_id'],
                                         session_id=data["session_id"]).first()
    sr.stopped_recording = True
    sr.started_recording = False
    counter = 0
    for p in StudioPresenter.query.filter_by(session_id=data['session_id'], stopped_recording=False, is_active=True, session_user_assoc_id=None).all():
        print(f"again stopped recording {p}")
        counter += 1
        # p.started_recording = False
        # p.stopped_recording = False
        socketio.emit("stop recording", {"external_user_id": p.external_user_id, "session_id": p.session_id}, room=f"room{p.sid}")
        socketio.emit("stop recording", {"external_user_id": p.external_user_id, "session_id": p.session_id}, room=p.sid)
    # if sr.session.start_recording:
    #     sr.session.start_recording = False
    if counter == 0:
        crud.update(StudioSession, {"id": data['session_id']}, {"start_recording": False})
    else:
        crud.db_commit()
    return True

@bp.route('/studio/sesison/recordings_dashboard/<int:studio_id>/<int:session_id>', methods=["GET"])
@tokenAuth.login_required
def studio_session_recording(studio_id, session_id):
    """
    Generate recording URLS for studio session
    """
    data = get_studio_session_recordings(studio_id, session_id, request.args.get("time_zone"))
    return jsonify({"data": data, "message": "Success", "status": 200}), 200

@bp.route("/logs/buffer/<int:session_id>", methods=["POST"])
def post_bufer_log(session_id):
    print(request.json)
    from app.models import BufferLog
    crud.create(BufferLog, {"session_id": session, "message": json.dumps(request.json)})
    return jsonify({"message": "Success", "status": 200}), 200