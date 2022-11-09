from flask import request, g, jsonify
from app.api import bp
from app.models.time_zone import TimeZone
from app.services.crud import CRUD
from app.services.auth import admin_user_authorizer
from app.api.user import tokenAuth

crud = CRUD()


@bp.route('/settings/time_zone', methods=["PUT"])
@tokenAuth.login_required
@admin_user_authorizer
def create_time_zone():
    crud.update(TimeZone, {"id": 1}, {"zone": request.json['zone'], "value": request.json['value']})
    return jsonify({"message": "Success", "status": 200}), 200


@bp.route('/settings/time_zone', methods=["GET"])
@tokenAuth.login_required
def get_time_zone():
    time_zone = TimeZone.query.filter_by(id=1).first()
    return jsonify(
        {"data": {"zone": time_zone.zone, "value": time_zone.value}, "message": "Success", "status": 200}), 200