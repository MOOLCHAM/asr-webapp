import pandas as pd
from flask import Blueprint, g, make_response, request, jsonify
from opensky_api import OpenSkyApi
from requests.exceptions import ReadTimeout


from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, select, func, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


from .map import initial_center


latLonBoundBox = [initial_center["lat"] - 3, initial_center["lat"] + 3, initial_center["lon"] - 3, initial_center["lon"] + 3]


try:
   # try to use the opensky API with credentials
   from ..secrets import OpenSkyCredentials


   opensky = OpenSkyApi(
       username=OpenSkyCredentials.USERNAME, password=OpenSkyCredentials.PASSWORD
   )
except ImportError:
   # if the username/password secrets weren't configured, use without credentials
   opensky = OpenSkyApi()


bp = Blueprint("Data", __name__, url_prefix="/data")


# Define the SQLAlchemy engine and session
engine = create_engine('mysql://root:<<password>>!@localhost/test_database')  # Update with your MySQL connection details
Session = sessionmaker(bind=engine)

# Define a base class for declarative class definitions
Base = declarative_base()


# Define the PlaneState model
class PlaneState(Base):
   __tablename__ = 'plane_states'


   id = Column(Integer, primary_key=True)
   icao24 = Column(String(6))
   callsign = Column(String(255))
   origin_country = Column(String(255))
   time_position = Column(Integer)
   last_contact = Column(Integer)
   longitude = Column(Float)
   latitude = Column(Float)
   geo_altitude = Column(Float)
   on_ground = Column(Boolean)
   velocity = Column(Float)
   true_track = Column(Float)
   vertical_rate = Column(Float)
   squawk = Column(String(255))
   position_source = Column(Integer)
   category = Column(Integer)


# Create the table in the database
Base.metadata.create_all(engine)


class airports(Base):
   __tablename__ = 'airports'


   id = Column(Integer, primary_key=True)
   ident = Column(String(4))
   type = Column(String(255))
   name = Column(String(255))
   latitude = Column(Float)
   longitude = Column(Float)
   elevation = Column(Integer)
   continent = Column(String(2))
   country_name = Column(String(255))
   iso_country = Column(String(2))
   region_name = Column(String(255))
   iso_region = Column(String(6))
   local_region = Column(String(2))
   municipality = Column(String(255))
   scheduled_service = Column(Boolean)
   gps_code = Column(String(6))
   iata_code = Column(String(6))
   local_code = Column(String(6))
   home_link = Column(String(255))
   wikipedia_link = Column(String(255))
   keywords = Column(String(255))
   score = Column(Integer)
  # last_updated(Integer)
   #stream_freqs(Integer)




airport_data = pd.read_excel(
   "data/us-airports.xlsx",
   usecols=[
       "ident",
       "type",
       "name",
       "latitude",
       "longitude",
       "elevation",
       "country_name",
       "region_name",
       "local_region",
       "municipality",
       "gps_code",
       "iata_code",
       "local_code",
       "home_link",
       "stream_freqs",
   ],
)




@bp.route("/plane_states")
def plane_states():
   session = Session()
   data = {"plane_data": []}


   try:
       states = opensky.get_states(
           bbox=(
               latLonBoundBox[0],
               latLonBoundBox[1],
               latLonBoundBox[2],
               latLonBoundBox[3],
           )
       )


       for state in states.states:
           plane_state = PlaneState(
               icao24=state.icao24,
               callsign=state.callsign,
               origin_country=state.origin_country,
               time_position=state.time_position,
               last_contact=state.last_contact,
               longitude=state.longitude,
               latitude=state.latitude,
               geo_altitude=state.geo_altitude,
               on_ground=state.on_ground,
               velocity=state.velocity,
               true_track=state.true_track,
               vertical_rate=state.vertical_rate,
               squawk=state.squawk,
               position_source=state.position_source,
               category=state.category
           )
           session.add(plane_state)


           # Append plane state data to the response
           data["plane_data"].append({
               "icao24": state.icao24,
               "callsign": state.callsign,
               "origin_country": state.origin_country,
               "time_position": state.time_position,
               "last_contact": state.last_contact,
               "longitude": state.longitude,
               "latitude": state.latitude,
               "geo_altitude": state.geo_altitude,
               "on_ground": state.on_ground,
               "velocity": state.velocity,
               "true_track": state.true_track,
               "vertical_rate": state.vertical_rate,
               "squawk": state.squawk,
               "position_source": state.position_source,
               "category": state.category,
               "category_icon": f"../static/images/markers/planeCategory{state.category}.svg", # f string format
           })


       session.commit()
       return jsonify(data), 200


   except ReadTimeout:
       session.rollback()
       return jsonify({"error": "Read timeout"}), 500


   finally:
       session.close()




@bp.route("/flight_track/<icao24>")
def flight_track(icao24):
   """
   Retrieves the flight track information of an aircraft specified by its ICAO 24-bit hexadecimal address.
   Data is retrieved from the OpenSky Network API.


   **Endpoint**: ``/data/flight_track/<icao24>``, ``<icao24>`` should be replaced with the ``icao24`` param (below)


   :param icao24: (required) ``String`` | ``str`` 24-bit hexadecimal address of the aircraft to lookup
   :returns: A JSON response with a root node called ``waypoints``, which is an array of JSON objects with the following keys:
   * ``time`` - (``Number`` | ``int``) Unix time in milliseconds that this waypoint was reached/logged
   * ``latitude`` - (``Number`` | ``float``) WGS84 latitude of the waypoint position
   * ``longitude`` - (``Number`` | ``float``) WGS84 longitude of the waypoint position
   """
   response_data = {"waypoints": []}


   if "flight_tracks" not in g:
       g.flight_tracks = {}


   try:
       track = opensky.get_track_by_aircraft(icao24)
       g.flight_tracks[icao24] = track
   except ReadTimeout:
       track = g.flight_tracks.get(icao24)
   finally:
       flight_path = track.path


   for waypoint in flight_path:
       response_data["waypoints"].append(
           {
               # convert from seconds since unix epoch to milliseconds for compatibility with JS Date API
               "time": waypoint[0] * 1000,
               "latitude": waypoint[1],
               "longitude": waypoint[2],
           }
       )


   return make_response(response_data, 200)




@bp.route("/airports/<state>")
def airports(state):
   """
   Retrieves airport data/metadata by state. This information is modified from the "List of US Airport"
   referenced at the end of the README. Airports are filtered by "large" and "medium" types, since the number
   of airports by state is, frankly, absurd.


   **Endpoint**: ``/data/airports/<state>``, ``<state>`` should be replaced with the ``state`` parameters (below)


   :param state: (required) ``String`` | ``str`` Two letter abbreviation of the state (e.g. FL for Florida)
   :returns: A JSON response with a root node called ``airport_data``, which is an array of JSON objects with the following keys:
   * ``ident`` - (``String`` | ``str``) Airport identification code
   * ``name`` - (``String`` | ``str``) Proper name of the airport
   * ``latitude`` - (``Number`` | ``float``) WGS84 Latitude of the airport
   * ``longitude`` - (``Number`` | ``float``) WGS84 Longitude of the airport
   * ``elevation`` - (``Number`` | ``float``) Elevation of the airport (from sea level), in feet
   * ``region_name`` - (``String`` | ``str``) Name of the region the airport is located within
   * ``local_region`` - (``String`` | ``str``) Local region of the airport
   * ``municipality`` - (``String`` | ``str``) Municipality the airport is located in
   * ``gps_code`` - (``String`` | ``str``) GPS code of the airport
   * ``iata_code`` - (``String`` | ``str``) IATA code of the airport
   * ``local_code`` - (``String`` | ``str``) Local code of the airport
   * ``home_link`` - (``String`` | ``str``) Link to the website/homepage of the airport's website, if available. ``null`` otherwise
   """
   response_data = {"airport_data": []}


   for row in airport_data.itertuples():
       if row.local_region == state:
           # filter by medium and large airports, because I didn't realize just
           # how many airports there are in the US
           if row.type == "large_airport" or row.type == "medium_airport":
               data = {
                   "ident": row.ident,
                   "name": row.name,
                   "latitude": row.latitude,
                   "longitude": row.longitude,
                   "elevation": row.elevation,
                   "region_name": row.region_name,
                   "local_region": row.local_region,
                   "municipality": row.municipality,
                   "gps_code": row.gps_code,
                   "iata_code": row.iata_code,
                   "local_code": row.local_code,
                   "home_link": row.home_link,
               }


               # filter out nan values
               for k, v in data.items():
                   if pd.isna(v):
                       # json lib doesn't encode nan values correctly, but does encode None correctly
                       data[k] = None


               if not pd.isna(row.stream_freqs):
                   data["tower_frequencies"] = row.stream_freqs.split(",")


               response_data["airport_data"].append(data)




   return make_response(response_data)

@bp.route("planes/<callsign>")
def planes(callsign):
    sign = callsign
    session = Session()
    response = {"plane_data": []}

    try:      
        data = session.query(PlaneState).filter(PlaneState.callsign==sign).first()
        
        response["plane_data"].append({
               "icao24": data.icao24,
               "callsign": data.callsign,
               "origin_country": data.origin_country,
               "time_position": data.time_position,
               "last_contact": data.last_contact,
               "longitude": data.longitude,
               "latitude": data.latitude,
               "geo_altitude": data.geo_altitude,
               "on_ground": data.on_ground,
               "velocity": data.velocity,
               "true_track": data.true_track,
               "vertical_rate": data.vertical_rate,
               "squawk": data.squawk,
               "position_source": data.position_source,
               "category": data.category,
               "category_icon": f"../static/images/markers/planeCategory{data.category}.svg", # f string format
           });

    except ReadTimeout:
       session.rollback()
       return jsonify({"error": "Read timeout"}), 500
    finally:
        session.close()

    return make_response(response)

    



@bp.route("/getMapLatLonBounds", methods=["POST"])
def getMapLatLonBounds():
   global latLonBoundBox
   latLonBoundBox = request.json['latLonBounds']
   return getLatLonBoundBox()


def getLatLonBoundBox():
   global latLonBoundBox
   return latLonBoundBox
