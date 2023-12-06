import os
from .blueprints import index, about, data, map, models
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy import create_engine
from pandas.core.frame import DataFrame
from sqlalchemy.orm import sessionmaker
from .blueprints.data import airport_data

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    engine = create_engine('sqlite://', echo=False)
    session = sessionmaker(engine)


    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI']  = 'sqlite:///' + os.path.join(basedir, 'communications.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)

    class Communication(db.Model):
        callsign = db.Column(db.String(9), primary_key=True)
        date = db.Column(db.Date)
        time = db.Column(db.Time)
        longitude = db.Column(db.String(13))
        latitude = db.Column(db.String(13))
        atc = db.Column(db.Boolean)
        audio = db.Column(db.BLOB)
        transcript = db.Column(db.BLOB)

        def __repr__(self):
            return f'<Communication {self.callsign}>'    

    class Flight(db.Model):
        flightNumber = db.Column(db.String(9))
        departLocation = db.Column(db.String(3))
        arrivalLocation = db.Column(db.String(3))
        callsign = db.Column(db.String(9), primary_key=True)

        def __repr__(self):
            return f'<Flight {self.callsign}>'

    class Airport(db.Model):
        ident = db.Column(db.Integer, primary_key=True)
        type = db.Column(db.String(15))
        name = db.Column(db.String(50))
        longitude = db.Column(db.String(13))
        latitude = db.Column(db.String(13))
        elevation = db.Column(db.Integer)
        country_name = db.Column(db.String(100))
        region_name = db.Column(db.String(30))
        local_region = db.Column(db.String(2))
        municipality = db.Column(db.String(50))
        gps_code = db.Column(db.String(4))
        iata_code = db.Column(db.String(3))
        local_code = db.Column(db.String(3))
        home_link = db.Column(db.String(500))
        stream_freqs = db.Column(db.String(500))

        def __repr__(self):
            return f'<Airport {self.iata_code}>'
    
    #airport_data.to_sql(name='Airport', con=engine, if_exists='replace', index='False')
    


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
