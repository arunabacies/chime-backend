from app.services.crud import CRUD
from datetime import datetime
from app.services.custom_errors import *
from app.models.projects import Project, ProjectUserAssociation
from app.models.presenter import Presenter
from app.models.event import Event
from app.models.room import Room
from config import Config
import json
import boto3
import pytz
from twilio.rest import Client
from app.services.multimedia import generate_pre_signed_url_multimedia, generate_session_url
crud = CRUD()


def video_call_presenter_validation(event_id: int, data: dict, ip_is: str) -> dict:
    """
    Chime first page itself will evaluate the login credentials and event expired or started
    """
    now = datetime.utcnow()
    media = []
    pr_obj = Presenter.query.filter_by(event_id=event_id, external_user_id=data['external_user_id']).join(
        Event).filter(Event.is_active == True).first()
    if not pr_obj:
        raise NoContent("This event has been deleted")
    if pr_obj.password != data['password']:
        raise BadRequest("Please enter the correct password and try again")
    if pr_obj.event.state == "upcoming":
        raise BadRequest("This event has not started yet!..")
    if pr_obj.event.state == "closed":
        raise BadRequest("This event has been expired!...")
    crud.update(Presenter, {"event_id": event_id, "external_user_id": pr_obj.external_user_id},
                {"ip_address": ip_is})
    if data.get('RoomId'):
        r = Room.query.filter_by(id=data['RoomId'], event_id=event_id).first()
        return {"id": pr_obj.id, "name": pr_obj.name, "external_user_id": pr_obj.external_user_id,
                "event_name": pr_obj.event.name, "event_id": pr_obj.event_id, 'mic': False, 'camera': False,
                "project_id": pr_obj.event.project_id, "media": [], "user_name": pr_obj.name, 
                'remote_audio_volume': 1.0, 'current_room': {}, 'broadcast_ndi': False, 'change_room_to': r.name, 
                'external_meeting_id': r.external_meeting_id, "user_role_id": 5, "ndi_webrtc_public_ip": pr_obj.ndi_webrtc_public_ip}
    for m in pr_obj.event.project.media:
        if not m.pre_signed_url or (now-m.updated).days>6:
            url = generate_pre_signed_url_multimedia(pr_obj.event.project_id, m.name, m.type_, m.id)
            print(m.to_dict())
            media.append(m.to_dict())
        else:
            media.append(m.to_dict())
    if not pr_obj.proj_user_assoc_id:
        ice_servers = json.loads(pr_obj.event.ice_server)
        if not ice_servers:
            ice_servers = twilio_create_new_stun_server()
            crud.update(Event, {"id": event_id}, {"ice_server": json.dumps(ice_servers)})
        if pr_obj.name == "ScreenRecorderBot":
            return {"id": pr_obj.id, "name": pr_obj.name, "external_user_id": pr_obj.external_user_id,
                "event_name": pr_obj.event.name, "event_id": pr_obj.event_id, "ice_servers": ice_servers,
                "project_id": pr_obj.event.project_id, "media": media, "user_role_id": 6, "recording": pr_obj.event.project.recording}    
        return {"id": pr_obj.id, "name": pr_obj.name, "external_user_id": pr_obj.external_user_id,
                "event_name": pr_obj.event.name, "event_id": pr_obj.event_id, "ice_servers": ice_servers,
                "project_id": pr_obj.event.project_id, "media": media, "user_role_id": 5, "ndi_webrtc_public_ip": pr_obj.ndi_webrtc_public_ip,
                "recording": pr_obj.event.project.recording}
    return {"id": pr_obj.id, "name": pr_obj.proj_assoc.user.name, "external_user_id": pr_obj.external_user_id,
                "event_name": pr_obj.event.name, "event_id": pr_obj.event_id,  "project_id": pr_obj.event.project_id, 
                "media": media, "user_role_id": pr_obj.proj_assoc.user.user_role}
                
def twilio_create_new_stun_server() -> dict:
    client = Client(Config.TWILIO_SID, Config.TWILIO_TOKEN)
    token = client.tokens.create(ttl=86400) # 24 hrs expiry
    stun, turn = "", {}
    for n in token.ice_servers:
        if  n.get("url").startswith("stun:"):
            if stun:
                continue
            stun = n.get("url").split('?')[0]
        elif n.get("url").startswith("turn:") and not turn:
            turn = n
            if stun:
                break
    ice_servers = {"iceServers": [{
        "urls": [stun.split('?')[0]]
        },
        {
            "username": turn.get('username'),
            "credential": turn.get('credential'),
            "urls": [
                turn.get('url').split('?')[0]
                ]}]}
    return ice_servers

def update_presenter_network_info(external_user_id: str, data: dict) -> bool:
    crud.update(Presenter, {"external_user_id": external_user_id}, {"network_info": json.dumps(data)})
    return True


def event_presenter_live_data(event_id: int) -> list:
    e = Event.query.filter_by(id=event_id).first()
    data= []
    if e:
        now = datetime.utcnow()
        for p in e.presenters:
            print(p)
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
                if u.avatar_file_name and (now - u.avatar_start_time).days > 6:
                    u.avatar = generate_session_url(f"avatar/{u.avatar_file_name}")
                    u.avatar_start_time = now
                    crud.db_commit()
                d['avatar'] = u.avatar
            data.append(d)
    return data


def get_event_presenter_details(project_id: int, event_id: int) -> list:    
    """
    Get the presenter details of an single event for edit
    """
    pr = Presenter.query.filter_by(event_id=event_id).all()
    presenters,presenters_count = [], 0
    now = datetime.utcnow()
    for p in pr:
        if p.name != "ScreenRecorderBot":
            if not p.email and not p.name:
                presenters.append({'id': p.id, 'external_user_id': p.external_user_id, 'avatar': p.avatar, 'avatar_file_name': p.avatar_file_name, 'name': p.proj_assoc.user.name, 
                'email': "", 'password': p.password})
            elif p.name and p.email:
                presenters_count += 1
                presenters.append({'id': p.id, 'external_user_id': p.external_user_id, 'avatar': p.avatar, 'avatar_file_name': p.avatar_file_name, 'name': p.name,
                 'email': p.email, 'password': p.password})
            if p.avatar_start_time and (now-p.avatar_start_time).days > 6:
                p.avatar = generate_session_url(f"project/{pr.event.project_id}/{pr.event_id}/avatar/{p.avatar_file_name}")
                p.avatar_start_time = now
                crud.db_commit()
    if presenters_count==0:
        raise NoContent()
    return presenters