from app import db
from app.models import BaseModel
import pytz
import json


FileType = {0: "image", 1: "song"}


class Multimedia(BaseModel):
    """
    Type: Image: 0
    Type: Song: 1
    """
    __tablename__ = "multimedia"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    local_name = db.Column(db.String(120), nullable=False)
    type_ = db.Column(db.Integer, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id", ondelete="CASCADE"), nullable=True)
    project = db.relationship("Project", backref="multimedia_project_details", uselist=False)
    
    pre_signed_url = db.Column(db.Text)

    def to_dict(self):
        data = dict(
            id=self.id,
            name=self.name,
            local_name=self.local_name,
            type_=FileType[self.type_],
            url=self.pre_signed_url
        )
        return data