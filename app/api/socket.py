from flask import jsonify, request, render_template
from flask_socketio import SocketIO, emit, send, join_room
from app import socketio
from app.models.presenter import Presenter
from app.models.studio import StudioPresenter
from app.services.crud import *
crud = CRUD()

@socketio.on('connect')
def socket_connect():
    print(f"connected***** {request.args}")
    if request.args.get("room"):
        join_room(request.args.get('room'))
        emit("event latest data", {"message": "just joined"}, room=request.args.get('room'))
        return True
    if request.args.get('external_user_id') != "null":
        if  request.args.get('event_id'):
            crud.update(Presenter, {"external_user_id": request.args.get('external_user_id'), 
            'event_id': request.args.get('event_id')}, {"sid": request.sid})
            print(f"Presenter**** > {request.sid}")
        elif request.args.get('session_id'): 
            crud.update(StudioPresenter, {"external_user_id": request.args.get('external_user_id'), 'session_id': request.args.get('session_id')}, {"sid": request.sid})
        emit('my response', {'data': 'Connected'}, room=f"room{request.sid}")
        emit('my response', {'data': 'Connected'}, room=request.sid)

@socketio.on_error_default
def default_error_handler(e):
    print(f"default_error_handler*** -> {e}")

@socketio.on('join')
def joined(data):
    """Sent by clients when they enter a room. A status message is broadcasted to all people in the room."""
    print(f"******************on_join****************** {data}")
    room = data['room']
    print(f"room is {data}")
    join_room(room)
    send(f"{request.sid} has entered the room***.", room=data['room'])
    return True

@socketio.on('response_test')
def response_test(data):
    print(f"response_test**")
    return True

@socketio.on('ping')
def ping():
    print(f"response_test PING **")
    socketio.emit("pong", request.sid)