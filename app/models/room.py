from app import db
from app.models import BaseModel
from uuid import uuid1
import json

class Room(BaseModel):
    __tablename__ = "room"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    rec_status = db.Column(db.Boolean, default=False)
    session_record_file = db.Column(db.String(50), default=str(uuid1()))
    broadcast_ndi = db.Column(db.Boolean, default=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id", ondelete="CASCADE"), nullable=False)
    proj_id = db.Column(db.Integer, db.ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    # Chime properties
    meeting_id = db.Column(db.String(40))  # Chime meeting_id
    external_meeting_id = db.Column(db.String(80))  # Chime external meeting id
    meeting_info = db.Column(db.Text)  # Chime meeting info
    active_members = db.Column(db.Text, default=json.dumps([]))
    recording_task_id = db.Column(db.Text)
    terminated_recording = db.Column(db.Boolean, default=False)
    # Relationship
    room_members = db.relationship("RoomMember", cascade="all, delete, delete-orphan", backref="room_room_members",
                                   lazy=True)
    presenters = db.relationship("Presenter", cascade="all, delete, delete-orphan", lazy=True, backref="room_presenter")
    event = db.relationship("Event", single_parent=True, backref="room_event_info", uselist=False)
    project = db.relationship("Project", single_parent=True, backref="room_project", uselist=False)


class RoomMember(BaseModel):
    __tablename__ = "room_member"
    id = db.Column(db.Integer, primary_key=True)
    proj_user_id = db.Column(db.Integer, db.ForeignKey("project_user_association.id", ondelete="CASCADE"), nullable=False)
    # attendee_id = db.Column(db.String(40))  # Chime user id
    # external_user_id = db.Column(db.String(60))  # Chime user external id
    # join_token = db.Column(db.Text) # User token exists when meeting is alive
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id", ondelete="CASCADE"), nullable=False)
    proj_user = db.relationship("ProjectUserAssociation", single_parent=True,
                                backref="room_member_project_user_association", uselist=False)
    user = db.relationship("User", single_parent=True, backref="room_member_user_pr_assigned", uselist=False)
    room = db.relationship("Room", single_parent=True, backref="room_member_rooms", uselist=False)
