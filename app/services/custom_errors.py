from flask import jsonify
from app.api import *


class CustomError(Exception):
    def __init__(self, message=None, status=None, payload=None):
        Exception.__init__(self)
        self.message = message
        self.status = status
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv.update({"message": self.message, "status": self.status})
        return rv


class NoContent(CustomError):
    def __init__(self, message="No data found."):
        CustomError.__init__(self, message, 404)


class BadRequest(CustomError):
    def __init__(self, message):
        CustomError.__init__(self, message, 400)


class Unauthorized(CustomError):
    def __init__(self, message="Please login and try again."):
        CustomError.__init__(self, message, 401)


class Forbidden(CustomError):
    def __init__(self, message="You do not have the privilege to do this."):
        CustomError.__init__(self, message, 403)


class InternalError(CustomError):
    def __init__(self, message="Please try again later."):
        CustomError.__init__(self, message, 500)


class UnProcessable(CustomError):
    def __init__(self, message="The input format is wrong"):
        CustomError.__init__(self, message, 422)


class Conflict(CustomError):
    def __init__(self, message="Duplicate Entry"):
        CustomError.__init__(self, message, 409)


@bp.errorhandler(CustomError)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = 200
    return response
