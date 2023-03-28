from datetime import datetime
import json
from dash import html, Input, Output, dcc, MATCH, callback_context
import dash
import dash_daq as daq
import dash_leaflet as dl
import pytz
from opensky_fetching import fetch_opensky
from transcribe_given_audio_file import Transcribe_ATC
import numpy as np
import pydub

dash.register_page(__name__, path='/')
app = dash.get_app()

#this object does the transcription
transcribe = Transcribe_ATC()

lat_min = -85.0
lat_max = -80.0
lon_min = 28.0
lon_max = 33.0
lat_start = -81.0598
lon_start = 29.1802
aeronautical_coords = {
    'lon_min': -175.2,
    'lon_max': -134,
    'lat_min': 81.47,
    'lat_max': 85,
    'lon_start': -150.28857327997687,
    'lat_start': 82.71605972541532
}

# TODO make active_map support multiple clients 
active_map = 0 # 0 = google map, 1 = aeronautical chart
all_planes_info = {}
selected_plane = None

def create_map_scale():
    return dl.ScaleControl(metric=False)

def create_plane_marker_container():
    return dl.MarkerClusterGroup(
        id="plane-markers",
        children=[],
        options={'disableClusteringAtZoom': True}
    )

def mark_plane(lat, long, name, angle):
    return dl.DivMarker(
        iconOptions={
            'html': f'<i class="plane fa fa-plane" style="transform: rotate({angle-45}deg);color: white;font-size: 25px;text-shadow: 0 0 3px #000;">', # Angle - 45 to account for the font awesome icon pointing 45 degrees northeast at 0 degrees rotation
            'className': ''
        },
        position=(lat, long),
        title=name,
        id={
            'type': 'plane',
            'index': name
        }
    )

# https://gamedev.stackexchange.com/a/32556
def scale_coords(x, src_min, src_max, dest_min, dest_max):
    return ( x - src_min ) / ( src_max - src_min ) * ( dest_max - dest_min ) + dest_min

def scale_lat(x):
    global active_map

    # Only scale coords if on aeronautical chart
    if active_map == 1:
        return scale_coords(x, 28, 32.25, aeronautical_coords['lat_min'], aeronautical_coords['lat_max'])
    else:
        return x

def scale_lon(x):
    global active_map

    # Only scale coords if on aeronautical chart
    if active_map == 1:
        return scale_coords(x, -85, -78.5, aeronautical_coords['lon_min'], aeronautical_coords['lon_max'])
    else:
        return x

def generate_popup_text(this_plane):
    

    stream_url = 'http://liveatc.net/kdab_del_gnd'
    with open('stream.wav', 'rb') as f:
        a = pydub.AudioSegment.from_mp3(f)
        y = np.array(a.get_array_of_samples())
        if a.channels == 2:
            y = y.reshape((-1, 2))

    f.close()
    #give this object a file path and it returns a string
    transcription = transcribe.transcribe_audio('stream.wav')

    return [
        transcription,
        f"Callsign: {this_plane.callsign}",
        f"Origin: {this_plane.origin_country}",
        f"Last Contact: {datetime.fromtimestamp(this_plane.last_contact, tz=pytz.timezone('America/New_York')).strftime('%m/%d/%Y %H:%M %Z')}",
        f"Location: ({this_plane.latitude}\u00B0, {this_plane.longitude}\u00B0)",
        f"Altitude: {this_plane.geo_altitude}m",
        f"Velocity: {this_plane.velocity} m/s",
        f"Track: {this_plane.true_track}\u00B0",
        f"Vertical Rate: {this_plane.vertical_rate} m/s",
        f"Squawk: {this_plane.squawk}",
    ]

# Mark all planes on interactive map
def generate_planes():
    global all_planes_info
    new_planes_info = fetch_opensky(lon_min, lon_max, lat_min, lat_max)

    # Only update planes if there are planes to update, otherwise do nothing. This caches the planes if nothing is found
    if new_planes_info:
        all_planes_info = {plane.callsign: plane for plane in new_planes_info}

    return [mark_plane(
        lat=scale_lat(all_planes_info[plane_name].latitude),
        long=scale_lon(all_planes_info[plane_name].longitude),
        name=all_planes_info[plane_name].callsign,
        angle=all_planes_info[plane_name].true_track
    ) for plane_name in all_planes_info]

def create_chart_tilelayer():
    return dl.TileLayer(
        url="/assets/output_files/{z}/{x}_{y}.jpeg",
        noWrap=True,
        tileSize=200,
        zoomOffset=6
    )

def create_image_map():
    return dl.Map(
    children=[create_chart_tilelayer()],
    zoom=8,
    maxZoom=9,
    minZoom=4,
    maxBounds=[[aeronautical_coords['lat_min'], aeronautical_coords['lon_min']], [aeronautical_coords['lat_max'], aeronautical_coords['lon_max']]],
    center=[aeronautical_coords['lat_start'], aeronautical_coords['lon_start']],
    id='image_map'
    )

# Renders the map into a file
# Shown by default
def create_interactive_map():
    return dl.Map(
        children=[
            dl.TileLayer(errorTileUrl="/assets/notile.png"), # Display error message in place of tiles when tiles can't be loaded
            create_map_scale(),
            create_plane_marker_container()
        ],
        id='interactive_map',
        zoom=13,
        center=(lon_start, lat_start),
    )

layout = html.Div(children=[
    html.Div(
        id="popup",
        children=[
            html.P("test")
        ],
        draggable="true"
    ),

    html.Div(id='map', children=[
        # Interactive map
        create_interactive_map(),

        # Image map
        create_image_map(),

        dcc.Interval(
            id='map-refresh',
            interval=15*1000 # 15 seconds 
        ),

        dcc.Interval(
            id='popup-refresh',
            interval=500 # 0.5 seconds 
        )
    ])
])

# Handler for when the toggle button is clicked
@app.callback(
    [Output('interactive_map', 'children'), Output('image_map', 'children'), Output('interactive_map', 'className'), Output('image_map', 'className')],
    [Input('map-switch', 'value')]
)
def update_output(value):
    global active_map
    active_map = 0 if not value else 1

    interactive_map_classname = "hidden" if value else ""
    image_map_classname = "" if value else "hidden"

    if value:
        # Toggle button activated: Image map
        # Toggle class and rewrite children for map
        return (
            [dl.TileLayer(),
            create_map_scale()],
            [create_chart_tilelayer(),
            create_map_scale(),
            create_plane_marker_container()],
            interactive_map_classname,
            image_map_classname
        )
    else:
        # Toggle button not activated: Interactive map
        # Toggle class and rewrite children for map
        return (
            [dl.TileLayer(),
            create_map_scale(),
            create_plane_marker_container()],
            [create_chart_tilelayer(),
            create_map_scale()],
            interactive_map_classname,
            image_map_classname
        )

# Update the plane markers at interval
@app.callback(Output('plane-markers', 'children'),
                Input('map-refresh', 'n_intervals'))
def update_map(n):
    p = generate_planes()
    return p

# Refresh the popup text at interval
@app.callback(Output('popup', 'children'),
              Input('popup-refresh', 'n_intervals'),
            prevent_initial_call=True)
def popup_refresh(n):
    if selected_plane and selected_plane in all_planes_info:
        return html.Div(children=[html.Span([item, html.Br()]) for item in generate_popup_text(all_planes_info[selected_plane])])

# Update the selected plane on click 
@app.callback(
    Output({'type': 'plane', 'index': MATCH}, 'n_clicks'),
    Input({'type': 'plane', 'index': MATCH}, 'n_clicks'),
    prevent_initial_call=True
)
def plane_click(n_clicks):
    global selected_plane
    selected_plane = json.loads(callback_context.triggered[0]['prop_id'][0:-9])['index']
    return None