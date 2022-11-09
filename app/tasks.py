from celery import Celery
from celery.app.registry import TaskRegistry
from flask import render_template
import requests
import json
import base64
import os
import time
import email
import re
from app.models import event, user
from config import Config
from app import db
from datetime import datetime, timedelta
from googleapiclient.discovery import build
import oauth2client
from oauth2client import client
from celery.schedules import crontab
from requests_oauthlib import OAuth2Session
import httplib2
from app.services.crud import CRUD
from googleapiclient.errors import *
from app.services.sendgrid_email import send_email
from app.models import User, Event, Presenter
from app.services.multimedia import create_cloudformation_stack, check_cloudformation_stack_status,get_stack_instances_state, pass_domain_to_nodejs
from app import create_app
import os
from constants import ALERT_EMAIL_TO

app = create_app()

app.app_context().push()


app = Celery('tasks',
             broker=os.environ.get('REDIS_URL'))
crud = CRUD()

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

app.conf.beat_schedule = {
    'add-every-5-minute': {
        'task': 'app.tasks.start_processing',
        'schedule': timedelta(minutes=1)
    },
    # 'add-daily-midnight': {
    #     'task': 'app.tasks.refresh_mindbody_daily_check',
    #     'schedule': crontab(minute=0, hour=0),
    # },
}
app.conf.timezone = 'UTC'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'


def auth_error_email(type_, to_email, user_id):
    # if not user_id:
    #     return True
    # user = User.query.filter_by(is_active=True).first()
    # print(f"auth_error_email {user}, {user.email}")
    # if not user or not user.is_active:
    #     return False
    # token = user.generate_auth_token(3600)
    # user.auth_token = token.decode('ascii')
    # db.session.add(user)
    # crud.update(Gma, {"email": user_id}, {"is_active": False})
    # crud.db_commit()
    # if type_ == "outlook":
    #     url = f"https://integration.ziplineplatform.com/outlook/signin?token={token.decode('ascii')}"
    #     send_email(to_email=[to_email, user_id], subject=f"Outlook Authentication Error {user_id}",
    #                html_content=f"<html><title>Zipline Error</title><body><p>Hi,<br>Please authenticate your Outlook account for syncing the leads to Zipline.</p><p><a href='{url}'>CLICK HERE<a></p></body></html>")
    #     print({"email": user_id}, {"is_active": False})
    #     crud.update(Mgoa, {"email": user_id}, {"is_active": False})
    # else:
    #     url = f"https://integration.ziplineplatform.com/gmail/login?token={token.decode('ascii')}"
    #     send_email(to_email=[to_email, user_id], subject=f"Gmail Authentication Error {user_id}",
    #                html_content=f"<html><title>Zipline Error</title><body><p>Hi,<br>Please authenticate your Gmail account for syncing the leads to Zipline.</p><p><a href='{url}'>CLICK HERE<a></p></body></html>")
    #     crud.update(Gma, {"email": user_id}, {"is_active": False})
    return True


# def get_gmail_auth(user_id, o_data, to_email):
#     return True
    # try:
    #     cred = oauth2client.client.GoogleCredentials(o_data['access_token'], Config.GOOGLE_CLIENT_ID, Config.GOOGLE_CLIENT_SECRET, o_data['refresh_token'], o_data['expires_at'], 'https://accounts.google.com/o/oauth2/token', 'Mozilla/5.0 (iPhone; CPU iPhone OS 5_1 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 Mobile/9B179 Safari/7534.48.3')
    # except Exception as e:
    #     send_email(to_email="arun_n_a@abacies.com", subject=f"Error {to_email} get_gmail_auth cred=",
    #                html_content=f"<body>{str(e)}</body>")
    #     auth_error_email("gmail", to_email, user_id)
    #     return False
    # try:
    #     service = build('gmail', 'v1', credentials=cred, cache_discovery=False)
    # except Exception as e:
    #     try:
    #         http = cred.authorize(httplib2.Http())
    #         cred.refresh(http)
    #         crud.update(Gma, {"email": user_id}, {"o_data": encrypt(json.dumps({'access_token': cred.access_token, 'expires_in': cred.token_expiry, 'refresh_token': cred.refresh_token, 'scope': o_data['scope'], 'token_type': o_data['token_type'], 'expires_at': cred.access_token_expired}))})
    #         service = build('gmail', 'v1', credentials=cred, cache_discovery=False)
    #     except Exception as e:
    #         send_email(to_email="arun_n_a@abacies.com", subject=f"Error {to_email} get_gmail_auth service 2 = ", html_content=f"<body>{str(e)}</body>")
    #         auth_error_email("gmail", to_email, user_id)
    #         return False
    # return service


@app.task
def golden_hour_alert(event_id: int, project_name: str, event_name: str, stack_id: str, stack_state: str):
    total_machines_required, failed_count, failed_machines, spawned_machines, not_associated_ip = 0, 0, [], [], []
    message = """<p>All Machines are not started yet for the event <b>"""+event_name+ """</b> of project <b>"""+project_name+"""</b></p><br>"""
    if stack_state == "CREATE_COMPLETE":
        message += f"<p>Stack Creation was success, StackId is {stack_id}</p><br>"
    for p in Presenter.query.filter_by(event_id=event_id).filter(Presenter.name!= 'ScreenRecorderBot').all():
        total_machines_required += 1
        if p.ndi_webrtc_instance:
            if p.ndi_webrtc_ec2_state == "running":
                spawned_machines.append(p.ndi_webrtc_public_ip)
            if not p.associated_ip:
                not_associated_ip.append(p.ndi_webrtc_instance or p.name)
            else:
                failed_machines.append(p.ndi_webrtc_public_ip)
        else:
            failed_count += 1
    created_machines_count = len(spawned_machines) + len(failed_machines)
    message = message + f"<p>Total machines required is <b>{total_machines_required}</b> and created <b>{spawned_machines}</b></p>" + "Running machines are <b>" + ", ".join(spawned_machines) + "</b> </p>" + "<p>These machines <b>" + ", ".join(failed_machines) +"</b> not started running yet.</p>"
    if not_associated_ip:
        message = message + "Elastic IP assigning is failed for " + ", ".join(not_associated_ip)
    send_email(to_email = ALERT_EMAIL_TO, subject=f"Golden Alert in session {event_name}", html_content=message)
    crud.update(Event, {"id": event_id}, {"golden_hour": True})

@app.task
def start_processing():
    print("start_processing***")
    now = datetime.utcnow()
    for ev in Event.query.filter_by(state='upcoming', node_api_call=False, webrtc_failed=False).filter(Event.event_time >= now - timedelta(days=1),
                                                                   Event.event_time < now + timedelta(days=1)).all():
        print(ev, ev.name)
        if ev.event_time - timedelta(minutes=Config.EVENT_PRE_TIME_STARTUP) >= datetime.utcnow():
            continue
        if not ev.stack_id:
            print("**No stack ID***")
            if not ev.machines_required or ev.machines_required<1:
                ev.machines_required = len(Presenter.query.filter_by(event_id=ev.id).filter(Presenter.name!= 'ScreenRecorderBot').all())
            if ev.machines_required>0:
                print("**create_cloudformation_stack")
                send_email(to_email = ALERT_EMAIL_TO, subject=f"Machine creation started {ev.name}", html_content=f"<p>Machine creation started for the event <b>{ev.name}</b of project <b>{ev.project.name}</b></p>")
                event_name = f"event-"+re.sub('[^\\w]', '', ev.name) + f"-{ev.id}-{ev.project_id}"
                create_cloudformation_stack(ev.id, event_name, ev.machines_required)
            continue
        if ev.golden_hour is False and ev.event_time - timedelta(hours=2) <= datetime.utcnow():
            print(f"Golden Alert {ev.name} {ev.id}")
            golden_hour_alert(ev.id, ev.project.name, ev.name, ev.stack_id, ev.stack_state)
        if not ev.stack_state or ev.stack_state == "CREATE_IN_PROGRESS":
            print("**CREATE_IN_PROGRESS")
            event_name = f"event-"+re.sub('[^\\w]', '', ev.name) + f"-{ev.id}-{ev.project_id}"
            cf_stack_status = check_cloudformation_stack_status(event_name)
            print(f"***cf_stack_status is  {cf_stack_status}")
            if cf_stack_status not in ["CREATE_COMPLETE", "CREATE_IN_PROGRESS"]:
                message = f"<p>Failed the Cloudformation Stack creation: <br> </p><p>Project: {ev.project.name}<br></p><p>Event: {ev.name}<br></p>"
                print(message)
                send_email(to_email = ALERT_EMAIL_TO, subject=f"Failed: Cloudformation Stack creation for event {ev.name}", html_content=message)
                crud.update(Event, {"id": ev.id}, {"stack_state": cf_stack_status, "webrtc_failed": True})
            else:
                print("**else update stack is completed***")
                crud.update(Event, {"id": ev.id}, {"stack_state": cf_stack_status})
            continue    
        if ev.stack_state  == "CREATE_COMPLETE" and not ev.machines_created:
            print("**calling get_stack_instances_state")
            get_stack_instances_state(ev.id, ev.stack_id, ev.name, ev.project.name)
        elif ev.machines_created and not ev.node_api_call:
            print("**calling pass_domain_to_nodejs")
            pass_domain_to_nodejs(ev.id, ev.name)
            print("**elif ev machines_created and pass domain to nodejs calls**")
        else:
            print("background else***")
    return True