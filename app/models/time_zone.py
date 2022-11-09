from app import db
from app.models import BaseModel


class TimeZone(BaseModel):
    __tablename__ = "time_zone"
    id = db.Column(db.Integer, primary_key=True)
    zone = db.Column(db.String(60), nullable=False)
    value = db.Column(db.String(10), nullable=False)
