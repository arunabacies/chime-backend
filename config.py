import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config(object):
    BASE_URL = os.environ.get("BASE_URL")
    FRONT_END_URL = os.environ.get("FRONT_END_URL")
    FRONT_END_PASSWORD_RESET_URL = os.environ.get("FRONT_END_PASSWORD_RESET_URL")
    FRONT_END_REGISTRATION_URL = os.environ.get("FRONT_END_REGISTRATION_URL")
    DEBUG = os.environ.get("DEBUG") or False
    PORT = os.environ.get("PORT")
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PASSWORD_RESET_SALT = os.environ.get("PASSWORD_RESET_SALT")
    SECRET_KEY = os.environ.get("SECRET_KEY")
    AUTH_TOKEN_EXPIRES = int(os.environ.get("AUTH_TOKEN_EXPIRES"))
    CRYPTO_KEY = os.environ.get("CRYPTO_KEY")
    SENDGRID_EMAIL_ADDRESS = os.environ.get("SENDGRID_EMAIL_ADDRESS")
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
    AVATAR_BUCKET_NAME = "w-call-avatar-test"
    BUCKET_REGION = "us-east-1"
    MEETING_URL=os.environ.get("MEETING_URL")
    SESSION_RECORDING_URL = os.environ.get("SESSION_RECORDING_URL")
    S3_MULTIMEDIA_BUCKET = os.environ.get("S3_MULTIMEDIA_BUCKET")
    SESSION_RECORDER_BUCKET = os.environ.get("SESSION_RECORDER_BUCKET")
    TWILIO_SID = os.environ.get("TWILIO_SID")
    TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN")
    STUDIO_MEETING_URL = os.environ.get("STUDIO_MEETING_URL")
    RECORDER_BACKEND_STUDIO_API = os.environ.get("RECORDER_BACKEND_STUDIO_API")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    DROPBOX_APP_KEY = os.environ.get("DROPBOX_APP_KEY")
    DROPBOX_APP_SECRET = os.environ.get("DROPBOX_APP_SECRET")
    CLOUDFORMATION_NDI_TEMPLATE = os.environ.get("CLOUDFORMATION_NDI_TEMPLATE")
    SUBNET_ID = os.environ.get("SUBNET_ID")
    EC2_IMAGE_ID = os.environ.get("EC2_IMAGE_ID")
    SECURITY_GROUP_ID = os.environ.get("SECURITY_GROUP_ID")
    EVENT_PRE_TIME_STARTUP = 150
    #  = os.environ.get("")


