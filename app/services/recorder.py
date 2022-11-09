import boto3
import datetime
import hashlib
import hmac 
import requests
from flask import g
from app import create_app
from config import Config
from app.models import Presenter, Project, Room, RoomMember, StudioPresenter, Event
import pytz
from app.services.custom_errors import *
from app.services.multimedia import client_s3, generate_session_url, resource_s3

def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

def getSignatureKey(key, dateStamp, regionName, serviceName):
    kDate = sign(('AWS4' + key).encode('utf-8'), dateStamp)
    kRegion = sign(kDate, regionName)
    kService = sign(kRegion, serviceName)
    kSigning = sign(kService, 'aws4_request')
    return kSigning

def get_signature() -> str:
    t = datetime.datetime.utcnow()
    amzdate = t.strftime('%Y%m%dT%H%M00Z')
    datestamp = t.strftime('%Y%m%d')
    canonical_headers = f"host:ec2.amazonaws.com\nx-amz-date:{amzdate}\n"
    payload_hash = hashlib.sha256(('').encode('utf-8')).hexdigest()
    canonical_request = 'GET\n/\nAction=DescribeRegions&Version=2013-10-15\n' + canonical_headers + '\nhost;x-amz-date\n' + payload_hash
    credential_scope = f"{datestamp}/us-east-1/execute-api/aws4_request"
    string_to_sign = 'AWS4-HMAC-SHA256' + '\n' +  amzdate + '\n' +  credential_scope + '\n' +  hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
    sig = getSignatureKey("nCHl53tCP5uZMzV7Xo06U4TiWZTkChH9UJGtWqT8", datestamp, 'us-east-1', ' apigateway')
    signature = hmac.new(sig, (string_to_sign).encode('utf-8'), hashlib.sha256).hexdigest()
    authorization_header = 'AWS4-HMAC-SHA256 Credential=' + "AKIAYDN3JX4C6ZWSQTFS" + '/' + credential_scope + ', SignedHeaders=host;x-amz-date, Signature=' + signature
    headers = {'X-Amz-Date':amzdate, 'Authorization':authorization_header}
    return headers


def start_chime_screen_recording(event_id: int, room_id: str, file_name: str) -> str:
    print(f"***start_chime_screen_recording {event_id} {room_id} {file_name}")
    # return True
    headers = get_signature()
    r = Presenter.query.filter_by(name='ScreenRecorderBot', event_id=event_id).first()
    meeting_url=f"{Config.MEETING_URL}?ExternalUserId={r.external_user_id}&ProjectId={r.event.project_id}&EventId={r.event_id}&p={r.password}&RoomId={room_id}&fileName={file_name}".replace("#", "%23").replace("&", "%26")
    url = f"{Config.SESSION_RECORDING_URL}?recordingAction=start&meetingURL={meeting_url}"
    print(f"recording url is___> {url}")
    response = requests.request("POST", url, headers=headers, data={})
    if response.status_code == 200:
        print("\n\n")
        print(response.text)
        print("\n\n")
        return response.json()
    print(response.json())
    return None

def stop_chime_screen_recording(task_id: str) -> bool:
    authorization_header = get_signature()
    url = f"{Config.SESSION_RECORDING_URL}?recordingAction=stop&taskId={task_id}"
    print(f"****stopchime recording url is {url}")
    headers = get_signature()
    response = requests.request("POST", f"{Config.SESSION_RECORDING_URL}?recordingAction=stop&taskId={task_id}", headers=headers)
    print(response)
    if response.status_code == 200:
        print(response.json())
        return True
    print(response.json())
    return False

# def get_recorder_files_complete_rooms(page, per_page: int, tz: str) -> tuple:
#     s3_client = client_s3()
#     rooms = Room.query.filter_by(rec_status=True).join(Project).filter(Project.recording==True).paginate(page, per_page, error_out=False)
#     data = [{"id": r.id, "name": r.name, "event_id": r.event_id, "event_name": r.event.name, "project_id": r.proj_id, 
#     "url": generate_session_url(f"{r.proj_id}/{r.event_id}/{r.session_record_file}.mp4", Config.SESSION_RECORDER_BUCKET, s3_client), "project_name": r.project.name, "event_time": r.event.event_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(tz)).strftime("%Y-%m-%dT%H:%M:%S")} for r in rooms.items]
#     if data:
#         return data, {"total": rooms.total, "current_page": rooms.page,
#                            "per_page": rooms.per_page, "length": len(data)}
#     raise NoContent()


def start_studio_screen_recording(session_id: int, file_name: str) -> str:
    print("start_studio_screen_recording")
    print("filname is", file_name)
    headers = get_signature()
    p = StudioPresenter.query.filter_by(name='ScreenRecorderBot', session_id=session_id).first()
    meeting_url=f"{Config.STUDIO_MEETING_URL}?ExternalUserId={p.external_user_id}&StudioId={p.session.studio_id}&StudioSessionId={session_id}&p={p.password}&fileName={file_name}".replace("#", "%23").replace("&", "%26")
    url = f"{Config.SESSION_RECORDING_URL}?recordingAction=start&meetingURL={meeting_url}"
    print(f"studio recording url is___> {url}")
    response = requests.request("POST", url, headers=headers, data={})
    print(response)
    if response.status_code == 200:
        print(response.json())
        return response.json()
    print(response.text)
