import pytz
import boto3
from datetime import datetime
from app import db
from app.models import BaseModel
from config import Config


class Project(BaseModel):
    __tablename__ = "project"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    # client_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    client_name = db.Column(db.String(120))
    job_number = db.Column(db.String(15))
    recording = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    creator = db.relationship("User",  primaryjoin="Project.created_by == User.id", backref="project_user_created_this",
                              uselist=False)
    # client = db.relationship("User",  primaryjoin="Project.client_id == User.id", backref="project_user_client",
                            #  uselist=False)
    assigned_users = db.relationship("ProjectUserAssociation", cascade="all, delete, delete-orphan",
                                     backref="project_project_user_association", lazy=True)
    events = db.relationship("Event", cascade="all, delete, delete-orphan", backref="project_event", lazy=True)
    rooms = db.relationship("Room", cascade="all, delete, delete-orphan", backref="project_room", lazy=True)
    media = db.relationship("Multimedia", cascade="all, delete, delete-orphan", backref="project_multimedia", lazy=True)

    def to_dict_list(self, tz):
        data = dict(
            id=self.id,
            name=self.name,
            job_number=self.job_number,
            is_active=self.is_active,
            recording=self.recording,
            client_name=self.client_name,
            # creator={'id': self.created_by, 'name': self.creator.name},
            created=self.created.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(tz)).strftime("%Y-%m-%dT%H:%M:%S"),
            events=len(self.events),
            # rooms=list(set(r.name for r in self.rooms)),
            members=[{'id': m.user_id, 'user_role': m.user.user_role, 'name': m.user.name} for m in self.assigned_users]
        )
        return data
    def to_dict(self, tz):
        data = dict(
            id=self.id,
            name=self.name,
            job_number=self.job_number,
            is_active=self.is_active,
            recording=self.recording,
            client_name=self.client_name,
            creator={"id": self.creator.id, "name": self.creator.name, "user_role": self.creator.user_role},
            created=self.created.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(tz)).strftime("%Y-%m-%dT%H:%M:%S"),
            events=[ev.to_dict(tz) for ev in self.events],
            media = [m.to_dict() for m in self.media],
            assigned_users=[{'id': u.id, 'user_id': u.user_id, 'name': u.user.name, 'email': u.user.email, 'user_role': u.user.user_role} for u in
                            self.assigned_users]
        )
        return data

    # def to_dict_single_project(self, tz):
    #     # can be delete after 
    #     data = dict(
    #         id=self.id,
    #         name=self.name,
    #         job_number=self.job_number,
    #         is_active=self.is_active,
    #         recording=self.recording,
    #         client_name=self.client_name,
    #         media=[m.to_dict() for m in self.media],
    #         creator={"id": self.creator.id, "name": self.creator.name, "user_role": self.creator.user_role},
    #         created=self.created.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(tz)).strftime("%Y-%m-%dT%H:%M:%S"),
    #         events=[ev.to_dict(tz) for ev in self.events],
    #         assigned_users=[{'id': u.id, 'user_id': u.user_id, 'name': u.user.name, 'email': u.user.email, 'user_role': u.user.user_role} for u in
    #                         self.assigned_users]
    #     )
  
        return data


class ProjectUserAssociation(BaseModel):
    __tablename__ = "project_user_association"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    user = db.relationship("User", single_parent=True, backref="project_user_association_user", uselist=False)
    project = db.relationship("Project", single_parent=True, backref="project_user_association_project_info",
                              uselist=False)
    creator_room = db.relationship("RoomMember", cascade="all, delete, delete-orphan", lazy=True,
                                   backref="project_user_association_room_member")
   
