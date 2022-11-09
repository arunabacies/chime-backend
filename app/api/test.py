from flask import jsonify, request, g, session, redirect
from flask.helpers import url_for
from app.api import bp

@bp.route('/', methods=["GET", "POST"])
def test_sget():
    print("test")
    print(request.json)
    print(request.args)
    # return redirect(url_for(index))
    return jsonify({"message": "Success"}), 200