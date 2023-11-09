import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func

from .blueprints import index, about, map, data, models


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI']  = 'sqlite:///' + os.path.join(basedir, 'communications.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)

    class Communication(db.Model):
        callsign = db.Column(db.String(9), primary_key=True)
        date = db.Column(db.Date)
        time = db.Column(db.Time)
        longitude = db.Column(db.Float(9, 6))
        latitude = db.Column(db.Float(9, 6))
        atc = db.Column(db.Boolean)

        def __repr__(self):
            return f'<Communication {self.callsign}>'

    class Flight(db.Model):
        flightNumber = db.Column(db.String(9))
        departLocation = db.Column(db.String(3))
        arrivalLocation = db.Column(db.String(3))
        callsign = db.Column(db.String(9), primary_key=True)

        def __repr__(self):
            return f'<Flight {self.callsign}>'

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    app.register_blueprint(index.bp)
    app.register_blueprint(about.bp)
    app.register_blueprint(map.bp)
    app.register_blueprint(data.bp)
 #   app.register_blueprint(models.bp)

    return app
