from app import db
from config import Config
from datetime import datetime


class BaseModel(db.Model):
    __abstract__ = True
    is_active = db.Column(db.Boolean, default=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    updated = db.Column(db.DateTime, default=db.func.now(), onupdate=datetime.utcnow)

    @classmethod
    def to_collection_dict(cls, url, page=1, per_page=20, **kwargs):
        resources = cls.query.paginate(page, per_page, False)
        data = {
            'item': [item.to_dict() for item in resources.items],
            '_meta': {
                'page': page,
                'per_page': per_page,
                'total_pages': resources.pages,
                'total_items': resources.total,
                'url': Config.BASE_URL + url
            }

        }
        return {"status": 200, "message": "success", "data": data.get('item', ""), "_meta": data.get('_meta', "")}, True

    def to_dict(self):
        pass
