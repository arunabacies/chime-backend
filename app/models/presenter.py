from sqlalchemy.orm import defaultload
from app import db
from app.models import BaseModel
import json


class Presenter(BaseModel):
    __tablename__ = "presenter"
    id = db.Column(db.Integer, primary_key=True)
    sid = db.Column(db.String(40)) # socket unique id for presenters
    name = db.Column(db.String(60))
    email = db.Column(db.String(60))

    avatar = db.Column(db.Text, nullable=True)
    avatar_file_name = db.Column(db.String(46), nullable=True)
    avatar_start_time = db.Column(db.DateTime)
    ip_address = db.Column(db.String(15))
    external_user_id = db.Column(db.String(60))  # Chime user external id
    # join_token = db.Column(db.Text) # User token exists when meeting is alive
    ndi_webrtc_public_ip = db.Column(db.String(50))
    ndi_webrtc_instance = db.Column(db.String(20))
    ndi_webrtc_ec2_state = db.Column(db.String(40))
    associated_ip = db.Column(db.Boolean, default=False)
    node_api_call = db.Column(db.Boolean, default=False)
    node_api_call_making = db.Column(db.Boolean, default=False)
    node_api_call_attempt = db.Column(db.Integer, default=0)
    room_history = db.Column(db.Text, default=json.dumps([]))
    current_room = db.Column(db.Text, default=json.dumps({}))
    password = db.Column(db.String(10))
    mic = db.Column(db.Boolean, default=True)
    camera = db.Column(db.Boolean, default=True)
    remote_audio_volume = db.Column(db.Float, default=1.0, nullable=True)
    network_info = db.Column(db.Text, default=json.dumps({}))
    proj_user_assoc_id = db.Column(db.Integer, db.ForeignKey("project_user_association.id", ondelete="CASCADE"))
    event_id = db.Column(db.Integer, db.ForeignKey("event.id", ondelete="CASCADE"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id", ondelete="CASCADE"), nullable=True)
    event = db.relationship("Event", single_parent=True, backref="presenter_event", uselist=False)
    room = db.relationship("Room", single_parent=True, backref="presenter_room", uselist=False)
    proj_assoc = db.relationship("ProjectUserAssociation", single_parent=True, backref="presenter_proj_assoc", uselist=False)


