import os
from flask import Flask

from .socketevents import socketio

from .blueprints import index, about, map, data, models, replay, site_map, contact

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config["DEBUG"] = True
    app.config["SECRET_KEY"] = "secret"

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    app.register_blueprint(index.bp)
    app.register_blueprint(about.bp)
    app.register_blueprint(map.bp)
    app.register_blueprint(data.bp)
    app.register_blueprint(replay.bp)
    app.register_blueprint(site_map.bp)
    app.register_blueprint(contact.bp)
    app.register_blueprint(models.bp)
    #app.register_blueprint()

    socketio.init_app(app)

    return app
