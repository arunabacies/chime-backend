from app import db
from app.services.custom_errors import *


class CRUD(object):
    def create(self, cls, data):
        try:
            record = cls(**data)
            db.session.add(record)
        except Exception as e:
            print(f"Please provide all fields correctly {str(e)}")
            raise BadRequest(f"Please provide all fields correctly")
        self.db_commit()
        return record

    def find(self, cls, condition):
        record = cls.query.filter_by(**condition).all()
        if record:
            return record
        raise NoContent()

    def get_by_id(self, cls, id_):
        record = cls.query.get(id_)
        if record:
            return record
        raise NoContent()

    def update(self, cls, condition, data):
        record = cls.query.filter_by(**condition).update(data)
        if record:
            self.db_commit()
            return record
        raise NoContent()

    def create_if_not(self, cls, condition, data):
        record = cls.query.filter_by(**condition).first()
        if not record:
            return self.create(cls, data)
        return record

    def create_or_update(self, cls, condition, data):
        record = cls.query.filter_by(**condition).first()
        if not record:
            return self.create(cls, data)
        return self.update(cls, condition, data)

    def bulk_insertion(self, cls, data):
        for record in data:
            i = cls(**record)
            db.session.add(i)
        self.db_commit()

    def delete(self, cls, condition):
        records = cls.query.filter_by(**condition).all()
        for record in records:
            db.session.delete(record)
            self.db_commit()
        return True

    def db_commit(self):
        try:
            db.session.commit()
            return True
        except Exception as e:
            print(str(e))
            db.session.rollback()
            raise InternalError()
