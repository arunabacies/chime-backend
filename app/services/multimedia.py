import boto3
from botocore.exceptions import ClientError
from flask.globals import request
from app.models import event
from config import Config
from app.models.presenter import Presenter
from app.services.crud import CRUD
from app.services.custom_errors import *
from app.models.multimedia import Multimedia
from app.models.event import Event
from app.services.utils import email_validation
import requests
from constants import IMAGE_EXTENSION, ELASTIC_IP, ALERT_EMAIL_TO
import uuid
import json
import base64
import threading
import queue
from datetime import datetime
from app.models.user import User
from app.services.sendgrid_email import send_email
crud = CRUD()
from app import create_app, db

thread_responses = queue.Queue()


def client_s3() -> object:
    s3_client = boto3.client('s3', aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
                             aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY)
    return s3_client


def resource_s3() -> object:
    s3 = boto3.resource('s3', aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY)
    return s3


def delete_s3_object(path: str, bucket_name: str = Config.S3_MULTIMEDIA_BUCKET, s3_client: object = None) -> bool:
    """
    Delete an object from s3
    """
    if not s3_client:
        s3_client = client_s3()
    print(f"path is {path}")
    s3_client.delete_object(Bucket=bucket_name, Key=path)
    return True


def generate_session_url(file_path: str, bucket_name : str = Config.S3_MULTIMEDIA_BUCKET, s3_client: object = None):
    print(f"file path: {file_path}")
    if not s3_client:
        s3_client = client_s3()
    response = s3_client.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': file_path},
                                                ExpiresIn=604800)
    print(f"response: {response}")
    return response


def file_upload_obj_s3(s3_client: object, file, path: str) -> dict:
    """
    Upload files to s3
    """
    s3_client.upload_fileobj(file, Config.S3_MULTIMEDIA_BUCKET, path, ExtraArgs={"ContentType": file.content_type})
    response = s3_client.generate_presigned_url(
        'get_object', Params={'Bucket': Config.S3_MULTIMEDIA_BUCKET, 'Key': path}, ExpiresIn=604800)
    return response


def upload_user_profile_pic(user_id: int, file: object) -> dict:
    """
    Upload user avatart and remove if an image already exist
    """
    file_extension = file.filename.split(".")[-1].upper()
    s3_client = client_s3()
    u = User.query.filter_by(id=user_id).first()
    if u.avatar_file_name:
        delete_s3_object(f"avatar/{u.avatar_file_name}", s3_client=s3_client)
    if file_extension not in IMAGE_EXTENSION:
        raise BadRequest("Invalid file extension")
    now = datetime.utcnow()
    new_file_name = f"{str(uuid.uuid1())}.{file.filename.split('.')[-1]}"
    response = file_upload_obj_s3(s3_client, file, f"avatar/{new_file_name}")
    return {"avatar": response, "avatar_file_name": new_file_name, "avatar_start_time": now}


def generate_pre_signed_url_multimedia(proj_id: int, name: str, type_: int, id_: int):
    s3_client = boto3.client('s3', aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
                             aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY)
    if type_ == 0:
        s3_obj_path = f"project/{proj_id}/multimedia/image/{name}"
    elif type_ == 1:
        s3_obj_path = f"project/{proj_id}/multimedia/song/{name}"
    response = s3_client.generate_presigned_url(
        'get_object', Params={'Bucket': Config.S3_MULTIMEDIA_BUCKET, 'Key': s3_obj_path}, ExpiresIn=604800)
    print(response)
    crud.update(Multimedia, {"id": id_}, {"pre_signed_url": response})
    return response


def delete_proj_multimedia(project_id: int, id_: int) -> bool:
    """
    Delete uploaded multimedia files from an project
    """
    m = Multimedia.query.filter_by(id=id_, project_id=project_id).first()
    if m:
        s3_client = client_s3()
        if m.type_ == 0:
            s3_obj_path = f"project/{project_id}/multimedia/image/{m.name}"
        elif m.type_ == 1:
            s3_obj_path = f"project/{project_id}/multimedia/song/{m.name}"
        delete_s3_object(s3_obj_path, s3_client=s3_client)
        db.session.delete(m)
        crud.db_commit()
    return True


def multimedia_upload(file: object, project_id: int):
    now = datetime.utcnow
    file_extension = file.filename.split(".")[-1].upper()
    if file_extension in IMAGE_EXTENSION:
        type_ = 0 # image type
        bucket_path = f"project/{project_id}/multimedia/image"
    elif file_extension == "MP3":
        type_ = 1 # mp3 file
        bucket_path = f"project/{project_id}/multimedia/song"
    else:
        raise BadRequest("Invalid file extension")
    new_file_name = f"{str(uuid.uuid1())}.{file.filename.split('.')[-1]}"
    s3_client = client_s3()
    response = file_upload_obj_s3(s3_client, file, f"{bucket_path}/{new_file_name}")
    crud.create(Multimedia, {"name": new_file_name, "type_": type_, "project_id": project_id,
                             "local_name": file.filename, "pre_signed_url": response})
    return True


def create_presenter(s3: object, s3_client: object, project_id: int, event_id: int, presenter: dict):
    """
    Add a presenter to db and upload image to s3
    """
    print(f"***create_presenter is  {presenter['email']}")
    email_validation(presenter.get('email'))
    if presenter.get('image_type'):
        file_extension = presenter['image_type'].split("/")[-1]
        print(file_extension)
        if file_extension.upper() not in IMAGE_EXTENSION:
            raise BadRequest(f"Invalid file extension {file_extension}")
        now = datetime.utcnow()
        new_file_name = f"{str(uuid.uuid1())}.{file_extension}"
        obj = s3.Object(Config.S3_MULTIMEDIA_BUCKET, f"project/{project_id}/{event_id}/avatar/{new_file_name}")
        obj.put(Body=base64.b64decode(presenter.pop('file')), ContentType=presenter.pop('image_type'))
        response = s3_client.generate_presigned_url('get_object', Params={
            'Bucket': Config.S3_MULTIMEDIA_BUCKET, 'Key': f"project/{project_id}/{event_id}/avatar/{new_file_name}"}, ExpiresIn=604800)
        presenter.update({'avatar': response, "avatar_file_name": new_file_name, "avatar_start_time": now})
    thread_responses.put(presenter)
    # pr = Presenter(event_id=event_id, **presenter)
    # db.session.add(pr)
    return True


def add_presenters(project_id: int, event_id: int, data: list) -> bool:
    """
    Add new presenters to an event
    """
    s3 = resource_s3()
    s3_client = client_s3()
    # print(f"add_presenters-- > {data}")
    elastic_ips = ELASTIC_IP
    assigned_ips = {p.ndi_webrtc_public_ip: elastic_ips.pop(p.ndi_webrtc_public_ip) for p in Presenter.query.filter_by(event_id=event_id).filter(Presenter.ndi_webrtc_public_ip != None).all()}
    elastic_ips = list(elastic_ips.keys())
    threads = []
    for c, p in enumerate(data):
        p.update({"ndi_webrtc_public_ip": elastic_ips[c]})
        print(f" P is --> {c}")
        t1 = threading.Thread(target=create_presenter, args=(s3, s3_client, project_id, event_id, p))
        t1.start()
        threads.append(t1)
        print(f"threads: {threads}")
        # create_presenter(s3, s3_client, project_id, event_id, p)
    for t in threads:
        print(t)
        print("join")
        t.join()
        data = thread_responses.get()
        print(f"data is {data}")
        pr = Presenter(event_id=event_id, **data)
        db.session.add(pr)
    # print(thread_responses.get())
    crud.db_commit()
    return True


def remove_presenter(project_id: int, event_id: int, presenter_ids: list) -> bool:
    """
    Remove presenters and their profile pic from S3
    """
    s3_client = client_s3()
    for pr in Presenter.query.filter_by(event_id=event_id).filter(Presenter.id.in_(presenter_ids)).all():
        if pr.avatar_file_name:
            delete_s3_object(f"project/{project_id}/{event_id}/avatar/{pr.avatar_file_name}", s3_client=s3_client)
        db.session.delete(pr)
    crud.db_commit()
    return True


def create_cloudformation_stack(event_id: int, stack_name: str, total_machines: str) -> dict:
    cf = boto3.client('cloudformation', aws_access_key_id="AKIAYZDEHMKLCPCPLZXM", aws_secret_access_key="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", region_name='us-east-1')
    stack_info = cf.create_stack(
        StackName=stack_name,
        TemplateURL=Config.CLOUDFORMATION_NDI_TEMPLATE,
        Parameters=[
            {"ParameterKey": "SubnetId", "ParameterValue": Config.SUBNET_ID},
            {"ParameterKey": "InstanceNos", "ParameterValue": str(total_machines)},
            {"ParameterKey": "InstanceType", "ParameterValue": "c4.2xlarge"},
            {"ParameterKey": "InstanceSecurityGroup", "ParameterValue": Config.SECURITY_GROUP_ID},
            {"ParameterKey": "AmiID", "ParameterValue": Config.EC2_IMAGE_ID}
            ],
        Tags=[{'Key': 'Name', 'Value': "arun-test-webcloud"}], 
        EnableTerminationProtection=False
        )
    crud.update(Event, {"id": event_id}, {"stack_id": stack_info.get('StackId'), "stack_details": json.dumps(stack_info)})
    return stack_info


def check_cloudformation_stack_status(stack_name: str):
    print("**check_cloudformation_stack_status")
    cf = boto3.client('cloudformation', aws_access_key_id="AKIAYZDEHMKLCPCPLZXM", aws_secret_access_key="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", region_name='us-east-1')
    st_info = cf.describe_stacks(StackName=stack_name)
    return st_info['Stacks'][0]['StackStatus']


def associate_address(client: object, instance_id: str, allocation_id: str, domain: str) -> bool:
    try:
        res = client.associate_address(DryRun=False, InstanceId=instance_id, AllocationId = allocation_id)
        if res.get('ResponseMetadata',{}).get('HTTPStatusCode') == 200:
            return True, res
        return False, res
    except Exception as e:
        return False, str(e)


def pass_domain_to_nodejs(event_id: int, event_name: str):
    print("pass_domain_to_nodejs**")
    success, failed = [], {}
    pp = Presenter.query.filter_by(event_id=event_id).filter(Presenter.name!= 'ScreenRecorderBot').first()
    if (datetime.utcnow()-pp.updated).seconds < 300:
        return False
    for count, pr in enumerate(Presenter.query.filter_by(event_id=event_id).filter(Presenter.name!= 'ScreenRecorderBot').all()):
        print(count, pr)
        if pr.node_api_call:
            success.append(pr.ndi_webrtc_public_ip)
        elif pr.node_api_call_making and (datetime.utcnow()-pr.updated_at).seconds < 300:
            print(f"pr.node_api_call_making--> {pr.node_api_call_making}")
            return False
        elif not pr.node_api_call and (pr.associated_ip and pr.ndi_webrtc_ec2_state == "running"):
            print(f"**elif**node_api_call --> {pr.node_api_call}")
            crud.update(Presenter, {"id": pr.id}, {"node_api_call_making": True})
            try:
                api_response = requests.post(url=f"https://{pr.ndi_webrtc_public_ip}/bot/url", headers={"Content-Type": "application/json"}, data=json.dumps({"url": f"https://{pr.ndi_webrtc_public_ip}"}))
                print(api_response)
                if api_response.status_code == 200 and api_response.json().get('message') == "success":
                    print(api_response.json())
                    crud.update(Presenter, {"id": pr.id}, {"node_api_call": True})
                    success.append(pr.ndi_webrtc_public_ip)
                else:
                    failed[pr.ndi_webrtc_public_ip] = pr.node_api_call_attempt + 1
                    crud.update(Presenter, {"id": pr.id}, {"node_api_call_attempt": pr.node_api_call_attempt + 1})
            except:
                failed[pr.ndi_webrtc_public_ip] = pr.ndi_webrtc_public_ip + 1
                crud.update(Presenter, {"id": pr.id}, {"node_api_call_attempt": pr.node_api_call_attempt + 1})
            finally:
                print("finallly *8")
                crud.update(Presenter, {"id": pr.id}, {"node_api_call_making": False})
    if len(success) == count + 1:
        crud.update(Event, {"id": event_id}, {"node_api_call": True})
        msg = f"NodeJs API call is success for the event {event_name} with domains " + ", ".join(success)
        send_email(to_email = ALERT_EMAIL_TO,  subject=f"Success: NodeJS API call for event {event_name}", html_content=msg)
    elif failed:
        attempts = any(f==5 for f in failed.values())
        if attempts:
            msg = f"NodeJs API call failed for the event {event_name} of domains " + ", ".join(list(failed.keys()))
            send_email(to_email = ALERT_EMAIL_TO,  subject=f"Failed: NodeJS API call for event {event_name}", html_content=msg)
    return True


def get_stack_instances_state(event_id: int, stack_id: str, event_name: str, project_name: str):
    print("**get_stack_instances_state")
    client = boto3.client('ec2', aws_access_key_id="AKIAYZDEHMKLCPCPLZXM", aws_secret_access_key="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", region_name='us-east-1')
    instances = client.describe_instances(Filters=[{'Name': 'tag:aws:cloudformation:stack-id', 'Values': [stack_id]}])
    instance_data, no_instance = {}, []
    pr_data = [{"ndi_webrtc_public_ip": pr.ndi_webrtc_public_ip, "ndi_webrtc_ec2_state": pr.ndi_webrtc_ec2_state, 
    "ndi_webrtc_instance": pr.ndi_webrtc_instance,"id": pr.id} for pr in Presenter.query.filter_by(event_id=event_id, associated_ip=False).filter(Presenter.name!= 'ScreenRecorderBot').all()]
    if not pr_data:
        crud.update(Event, {"id": event_id}, {"machines_created": True})
        success_ids = [f"{pr.ndi_webrtc_instance} ({pr.ndi_webrtc_public_ip})" for pr in Presenter.query.filter_by(event_id=event_id, associated_ip=False).filter(Presenter.name!= 'ScreenRecorderBot').all()]
        html_content=f"Successfully started all machines for event {event_name} of project {project_name}" + ", ".join(success_ids)
        send_email(to_email = ALERT_EMAIL_TO, subject=f"Success: Cloudformation Stack creation for event {event_name}", html_content=html_content)
    for i in instances.get('Reservations', []):
        for e in i['Instances']:
        # instance_data[e.get('InstanceId')] = {'instance_id': e.get('InstanceId'), 'state': e.get('State', {}).get('Name'), 
        # 'launch_time': e.get('LaunchTime'), 'public_ip_address': e.get('PublicIpAddress')}
            instance_data[e.get('InstanceId')] = {'instance_id': e.get('InstanceId'), 'state': e.get('State', {}).get('Name'), 
        'launch_time': e.get('LaunchTime')}
    for p in pr_data:
        record = {}
        if p.get("ndi_webrtc_instance"):
            ins = instance_data.pop(p.get("ndi_webrtc_instance"))
            if p.get("ndi_webrtc_ec2_state") != ins['state']:
                record['ndi_webrtc_ec2_state'] = ins['state']
            # if not p.get("ndi_webrtc_public_ip"):
            #     record["ndi_webrtc_public_ip"] = p.get("ndi_webrtc_public_ip")
            if ins['state'] == "running":
                assoc_ip_status, ip_response = associate_address(client, p.get("ndi_webrtc_instance"), 
                ELASTIC_IP.get(p['ndi_webrtc_public_ip'])['allocation_id'], p['ndi_webrtc_public_ip'])
                if assoc_ip_status:
                    record['associated_ip'] = True
                else:
                    send_email(to_email = ALERT_EMAIL_TO, 
                    subject=f"Failed elastic IP assignment in event {event_name}", 
                    html_content=f"something wrong with elastic ip assigning process for the instance {p['ndi_webrtc_instance']} and domain {ndi_webrtc_public_ip}. Error message is : {ip_response}")
            if record:
                crud.update(Presenter, {"id": p['id']}, record)
        else:
            no_instance.append(p)
    if no_instance:
        instance_data = list(instance_data.values())
        for c, p in enumerate(no_instance):
            ins = instance_data[c]
            # crud.update(Presenter, {"id": p['id']}, {"ndi_webrtc_ec2_state": ins['state'], 
            # 'ndi_webrtc_public_ip': ins['public_ip_address'], "ndi_webrtc_instance": ins["instance_id"]})
            crud.update(Presenter, {"id": p['id']}, {"ndi_webrtc_ec2_state": ins['state'], "ndi_webrtc_instance": ins["instance_id"]})
    return True
