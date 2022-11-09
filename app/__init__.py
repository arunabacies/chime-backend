import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from config import Config
from flask_socketio import SocketIO
db = SQLAlchemy()
migrate = Migrate()
# socketio = SocketIO(cors_allowed_origins="*", message_queue=Config.RABBITMQ_URL)
socketio = SocketIO(cors_allowed_origins="*", ping_timeout=10, ping_interval=5)

app = None

def create_app(config_class=Config):
    print("called created aaappp***")
    global app
    if app:
        print("appppp")
        return app
    app = Flask(__name__, template_folder='templates')
    CORS(app)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    # initialize socketio
    socketio.init_app(app, engineio_logger=True, logger=True)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = RotatingFileHandler('log_data_cr.log', maxBytes=10000, backupCount=2)
    file_handler.setFormatter(formatter)
    logging.basicConfig(handlers=[file_handler], level=logging.DEBUG)
    logger = logging.getLogger('log_data_cr.log')
    app.logger.addHandler(file_handler)
    from app.api import bp as api_bp
    app.register_blueprint(api_bp)
    from app.api.dropbox_api import dropbox_blueprint
    app.register_blueprint(dropbox_blueprint)
    print("gm == apppp***")
    return app


from app import models
