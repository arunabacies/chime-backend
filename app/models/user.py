from app import db
from config import Config
from werkzeug.security import generate_password_hash, check_password_hash
from flask_httpauth import HTTPBasicAuth
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
from app.models import BaseModel

auth = HTTPBasicAuth()


class User(BaseModel):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    sid = db.Column(db.String(40)) # socket id
    # Credential
    email = db.Column(db.String(50), index=True, unique=True, nullable=False)
    hashed_password = db.Column(db.Text)

    # User information
    name = db.Column(db.String(120))
    user_role = db.Column(db.Integer, default=3, nullable=True)
    # user_role = db.Column(db.Integer, default=3)
    registered = db.Column(db.Boolean, default=False)
    avatar = db.Column(db.Text, nullable=True)
    avatar_file_name = db.Column(db.String(46), nullable=True)
    avatar_start_time = db.Column(db.DateTime)

    # Relationships
    creator_project = db.relationship("Project", primaryjoin="User.id == Project.created_by", backref="user_project",
                                      cascade="all, delete, delete-orphan", lazy=True)
    creator_event = db.relationship("Event", primaryjoin="User.id == Event.created_by", backref="user_event_create",
                                    cascade="all, delete, delete-orphan", lazy=True)
    # client_project = db.relationship("Project", primaryjoin="User.id == Project.client_id", lazy=True,
    #                                  cascade="all, delete, delete-orphan", backref="user_client_project")
    project_assigned = db.relationship("ProjectUserAssociation", cascade="all, delete, delete-orphan", lazy=True,
                                       backref="user_assigned_projects_list")
    room_members = db.relationship("RoomMember", cascade="all, delete, delete-orphan", lazy=True, backref="user_t_room")
    studio_user_assoc= db.relationship("StudioUserAssociation", cascade="all, delete, delete-orphan", lazy=True, backref="user_studio_mem")
    
    def to_dict(self):
        data = dict(
            id=self.id,
            name=self.name,
            email=self.email,
            # country_code=self.country_code,
            # phone=self.phone,
            is_active=self.is_active,
            registered=self.registered,
            user_role=self.user_role,
            avatar_file_name=self.avatar_file_name,
            avatart=self.avatar
        )
        return data

    def get_hashed_password(self, password):
        return generate_password_hash(password)

    def hash_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)

    def generate_auth_token(self, expiration=Config.AUTH_TOKEN_EXPIRES):
        s = Serializer(Config.SECRET_KEY, expires_in=expiration)
        print(self.id, self.name)
        return s.dumps({'id': self.id, 'user_role': self.user_role})

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(Config.SECRET_KEY)
        print(token)
        try:
            data = s.loads(token)
            return data
        except (SignatureExpired, BadSignature):
            return None
        # user = User.query.filter_by(id=data.get('id', ''), is_active=True).first()
        # return user
