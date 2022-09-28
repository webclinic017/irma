import json
import os
from datetime import timedelta

from fakeredis import FakeRedis
from flask import Flask

# da togliere
from flask_cors import CORS
from flask_redis import FlaskRedis
from flask_socketio import SocketIO

from .services.database import init_db
from .services.jwt import init_jwt
from .services.mqtt import create_mqtt
from .services.scheduler import init_scheduler
from .services.socketio import init_socketio

# interval for checking sensor timeout
SENSORS_UPDATE_INTERVAL = timedelta(seconds=10)

# for testing purposes
# TODO: move to config file
DISABLE_MQTT = False if os.environ.get("DISABLE_MQTT") != 1 else True


socketio = SocketIO(cors_allowed_origins="*")
mqtt = None
redis_client = FlaskRedis()


def create_app(testing=False, debug=False):
    app = Flask(__name__)
    global mqtt
    global redis_client

    app.config.from_file("../config/config.json", load=json.load)
    if testing:
        app.config.from_file("../config/config_testing.json", load=json.load)
        redis_client = FlaskRedis.from_custom_provider(FakeRedis)
        print(f"{redis_client=}")

    app.debug = debug

    redis_client.init_app(app)
    init_scheduler(app, SENSORS_UPDATE_INTERVAL.total_seconds())
    init_jwt(app)
    init_db(app)
    CORS(app)

    if not DISABLE_MQTT:
        mqtt = create_mqtt(app)

    from .blueprints.api import bp

    app.register_blueprint(bp)
    socketio.init_app(app)

    init_socketio(socketio)

    return app
