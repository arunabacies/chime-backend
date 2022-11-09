from collections import defaultdict
from app import db
from app.models import BaseModel
import pytz
import json
# from datetime import datetime
# from app.services.multimedia import generate_session_url

class Event(BaseModel):
    __tablename__ = "event"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    event_time = db.Column(db.DateTime)
    state = db.Column(db.String(20), default="upcoming") # upcoming, running, closed
    # instances = db.Column(db.Text, default=json.dumps({})) # instances created for meeting presenters
    # instance_created = db.Column(db.String(30), default="notYet") # notYet, started, yes
    project_id = db.Column(db.Integer, db.ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    ice_server = db.Column(db.Text, default=json.dumps({}))
    golden_hour = db.Column(db.Boolean, default=False)
    event_queued = db.Column(db.Boolean, default=False)
    machines_created = db.Column(db.Boolean, default=False)
    node_api_call = db.Column(db.Boolean, default=False)
    stack_id = db.Column(db.Text)
    stack_details = db.Column(db.Text)
    stack_state = db.Column(db.String(40))
    webrtc_failed = db.Column(db.Boolean, default=False)
    machines_required = db.Column(db.Integer)
    creator = db.relationship("User", backref="event_user_created", uselist=False)
    project = db.relationship("Project", backref="event_project_details", uselist=False)
    rooms = db.relationship("Room", cascade="all, delete, delete-orphan", backref="event_room",
                            order_by='Room.id.asc()', lazy=True)
    presenters = db.relationship("Presenter", cascade="all, delete, delete-orphan", backref="event_presenter",
                                 lazy=True)


    def to_dict(self, tz):
        data = dict(
            id=self.id,
            name=self.name,
            event_time=self.event_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(tz)).strftime(
                "%Y-%m-%dT%H:%M:%S") if self.event_time else None,
            state=self.state,
            project_id=self.project_id,
            created_by=self.created_by,
            is_active=self.is_active,
            rooms=[{"id": r.id, "name": r.name, "broadcast_ndi": r.broadcast_ndi,"members": [
                {'id': m.id, 'user_id': m.user_id, 'name': m.user.name, 'user_role': m.user.user_role,
                 'email': m.user.email} for m in r.room_members]} for r in self.rooms], 
            presenters=[
                {'id': p.id, 'external_user_id': p.external_user_id, 'avatar': p.avatar, 'avatar_file_name': p.avatar_file_name, 'name': p.name,
                 'email': p.email, 'password': p.password} for p in self.presenters if p.name != "ScreenRecorderBot"]
        )
        return data

    def to_dict_for_single_proj(self, tz):
        data = dict(
            id=self.id,
            name=self.name,
            event_time=self.event_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(tz)).strftime(
                "%Y-%m-%dT%H:%M:%S") if self.event_time else None,
            state=self.state,
            project_id=self.project_id,
            is_active=self.is_active,
            rooms=len(self.rooms),
            presenters=len(self.presenters)
        )
        # tod =o minus bot if recording else pass
        if self.project.recording:
            data['presenters'] = data['presenters'] - 1
        return data