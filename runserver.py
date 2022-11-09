from app import create_app, db, socketio
from app.models import User
from flask import request
import logging
from logging.handlers import RotatingFileHandler
# from flask_socketio import SocketIO, emit, send

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User}



if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', debug=app.config["DEBUG"], port=app.config["PORT"], pingInterval = 10000, pingTimeout= 5000)
    # app.run(host='0.0.0.0', debug=app.config["DEBUG"], port=app.config["PORT"])
