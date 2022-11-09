import pytz
from datetime import datetime
from app import db
from app.models import BaseModel
from config import Config
from collections import defaultdict
import json

class Studio(BaseModel):
    __tablename__ = "studio"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    client_name = db.Column(db.String(120))
    job_number = db.Column(db.String(15))
    recording = db.Column(db.Integer, default=1) # 1: Audio & Video 2.Audio Only 3: Video Only
    storage_source = db.Column(db.Integer, default=1) #1: WorldStage AWS 2: GoogleDrive, 3: Dropbox
    storage_credential = db.Column(db.Text, default=json.dumps({}))
    storage_details =  db.Column(db.Text, default=json.dumps({}))
    created_by = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    creator = db.relationship("User",  primaryjoin="Studio.created_by == User.id", backref="studio_user_created_this",
                              uselist=False)
    assigned_users = db.relationship("StudioUserAssociation", cascade="all, delete, delete-orphan",
                                     backref="studio_user_assoc", lazy=True)
    sessions = db.relationship("StudioSession", cascade="all, delete, delete-orphan", backref="studio_studio_session", lazy=True)
    

    def to_dict_list(self, tz):
        data = dict(
            id=self.id,
            name=self.name,
            client_name=self.client_name,
            job_number=self.job_number,
            recording=self.recording,
            is_active=self.is_active,
            created_at=self.created.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(tz)).strftime("%Y-%m-%dT%H:%M:%S"),
            sessions=len(self.sessions),
            members=[{'id': m.id,'user_id': m.user_id, 'user_role': m.user.user_role, 'name': m.user.name} for m in self.assigned_users]
        )
        return data


class StudioUserAssociation(BaseModel):
    __tablename__ = "studio_user_association"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    studio_id = db.Column(db.Integer, db.ForeignKey("studio.id", ondelete="CASCADE"), nullable=False)
    user = db.relationship("User", single_parent=True, backref="studio_user_assoc_user", uselist=False)
    studio = db.relationship("Studio", single_parent=True, backref="studio_user_assoc_studio_info",
                              uselist=False)


class StudioSession(BaseModel):
    __tablename__ = "studio_session"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    session_time = db.Column(db.DateTime)
    external_meeting_id = db.Column(db.String(120), nullable=True)
    start_recording = db.Column(db.Boolean, default=False)
    state = db.Column(db.String(20), default="upcoming") # upcoming, running, closed
    file_name = db.Column(db.String(50))
    recording_task_id = db.Column(db.Text)
    studio_id = db.Column(db.Integer, db.ForeignKey("studio.id", ondelete="CASCADE"), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    creator = db.relationship("User", backref="studio_user_created", uselist=False)
    studio = db.relationship("Studio", backref="session_studio_details", uselist=False)
    members = db.relationship("StudioSessionMember", cascade="all, delete, delete-orphan", backref="s_s_m_s_session", lazy=True)
    presenters = db.relationship("StudioPresenter", cascade="all, delete, delete-orphan", backref="studio_presenter", lazy=True)


class StudioSessionMember(BaseModel):
    __tablename__ = "studio_session_member"
    id = db.Column(db.Integer, primary_key=True)
    studio_user_id = db.Column(db.Integer, db.ForeignKey("studio_user_association.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    studio_session_id = db.Column(db.Integer, db.ForeignKey("studio_session.id", ondelete="CASCADE"), nullable=False)
    studio_users = db.relationship("StudioUserAssociation", single_parent=True,
                                backref="studio_session_member_s_user_assoc", uselist=False)
    user = db.relationship("User", single_parent=True, backref="session_member_s_s_m", uselist=False)
    studio_session = db.relationship("StudioSession", single_parent=True, backref="s_s_m", uselist=False)

class StudioPresenter(BaseModel):
    __tablename__ = "studio_presenter"
    id = db.Column(db.Integer, primary_key=True)
    sid = db.Column(db.String(40)) # socket unique id for presenters
    name = db.Column(db.String(60))
    email = db.Column(db.String(60))
    # avatar = db.Column(db.Text, nullable=True)
    # avatar_file_name = db.Column(db.String(46), nullable=True)
    # avatar_start_time = db.Column(db.DateTime)
    stored = db.Column(db.Boolean, default=False, nullable=False)
    started_recording = db.Column(db.Boolean, default=False)
    stopped_recording = db.Column(db.Boolean, default=False)
    ip_address = db.Column(db.String(15))
    external_user_id = db.Column(db.String(60))  # Chime user external id
    password = db.Column(db.String(10))
    mic = db.Column(db.Boolean, default=True)
    camera = db.Column(db.Boolean, default=True)
    remote_audio_volume = db.Column(db.Float, default=1.0, nullable=True)
    network_info = db.Column(db.Text, default=json.dumps({}))
    session_id = db.Column(db.Integer, db.ForeignKey("studio_session.id", ondelete="CASCADE"), nullable=False)
    session_user_assoc_id = db.Column(db.Integer, db.ForeignKey("studio_session_member.id", ondelete="CASCADE"))
    session = db.relationship("StudioSession", single_parent=True, backref="studio_pre_ses", uselist=False)
    session_user_assoc = db.relationship("StudioSessionMember", single_parent=True, backref="pr_session_assoc", uselist=False)


