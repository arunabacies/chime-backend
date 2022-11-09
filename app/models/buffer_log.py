from app import db
from app.models import BaseModel
import pytz
import json


class BufferLog(BaseModel):
    """
    Store the error log if chime to nodejs failed
    """
    __tablename__ = "buffer_log"
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(120), nullable=False)
    session_id = db.Column(db.Integer, nullable=False)