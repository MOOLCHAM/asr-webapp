var map = L.map('map').fitWorld();

// Organize different elements into groups (makes it easier to clear and redraw markers on update)
var planeLayer = L.layerGroup().addTo(map).setZIndex(600);          // For plane markers
var airportLayer = L.layerGroup().addTo(map).setZIndex(600);        // For airport markers
var infoLayer = L.layerGroup().addTo(map).setZIndex(800);           // For info pane
var flightPathLayer = L.layerGroup().addTo(map).setZIndex(550);     // For flight path lines

var planeData = [];
var airportData = [];

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: "&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors"
}).addTo(map);

/**
 * Decodes a transponder type to the string version (i.e. int -> string). Useful for displaying this data in the UI.
 *
 * @param {int} position_source the position source from the API endpoint
 * @returns {string} transponder source type
 */
function get_position_source_string(position_source) {
    var source = "";

    // From the API docs for OpenSky
    switch (position_source) {
        case 0:
            source = "ADS-B";
            break;
        case 1:
            source = "ASTERIX";
            break;
        case 2:
            source = "MLAT";
            break;
        case 3:
            source = "FLARM";
            break;
        default:
            source = "N/A";
    }

    return source;
}

/**
 * Clears the table in the info pane in preparation for new data.
 */
function clear_table() {
    // Remove previous data
    $("#infoPane tr").each(function (index) {
        if ($(this).attr("id") != "tableHeader")
            $(this).remove();
    });
}

/**
 * Decodes a plane category from the integer representation (i.e. int -> string)
 *
 * @param {int} category plane category from API endpoint
 * @returns {string} decoded plane category
 */
function get_plane_category_string(category) {
    var category = "";

    // TODO: there are a lot of categories to cover here
    switch (category) {
        default:
            category = "Unknown";
    }

    return category;
}

/**
 * Draws the estimated flight path of the plane specified by the ICAO 24-bit address (from as far back as the waypoints go to
 * its current position).
 *
 * @param {string} icao24 24-bit ICAO identification number. This is a hexadecimal number represented as a string in the API.
 */
function draw_flight_path(icao24) {
    const flight_path_request = new XMLHttpRequest();

    flight_path_request.addEventListener("load", function () {
        if (flight_path_request.response == null)
            return;

        var waypoint_coords = [];
        flightPathLayer.clearLayers();

        for (const waypoint of flight_path_request.response.waypoints) {
            waypoint_coords.push([waypoint.latitude, waypoint.longitude]);

            let waypointMark = L.circleMarker(
                [waypoint.latitude, waypoint.longitude],
                {
                    radius: 10,
                    color: "black",
                    fill: true,
                    opacity: 1.0
                }
            ).addTo(flightPathLayer);

            let waypoint_time = new Date(waypoint.time);

            waypointMark.on('mouseover', function () {
                L.popup(
                    [waypoint.latitude, waypoint.longitude],
                    {
                        content: `Time: ${waypoint_time.toLocaleString()}<br />Location: ${waypoint.latitude}\u00b0N ${waypoint.longitude}\u00b0W`
                    }
                ).openOn(map);
            });
        }

        L.polyline(waypoint_coords, {
            color: "#000000",
            noClip: true,
            smoothFactor: 0
        }).addTo(flightPathLayer);
    });

    flight_path_request.open("GET", `/data/flight_track/${icao24}`);
    flight_path_request.responseType = "json";
    flight_path_request.send();
}

/**
 * Draws the plane markers on the Leaflet map based on the latitude, longitude, and heading information.
 * Also sets up the callback for the click event to populate the table in the information pane and draw flight path(s).
 *
 * @param {Array} plane_data An array of objects associated with a valid API response (i.e. response body isn't null).
 */
function draw_plane_markers(plane_data) {
    planeLayer.clearLayers();

    for (const plane of plane_data) {
        let marker = L.marker({
            lat: plane.latitude,
            lng: plane.longitude,
        });

        // order in which these methods are called doesn't matter
        marker.setIcon(planeIcon);
        // Rotate icon to match actual plane heading
        marker.setRotationAngle(plane.true_track);
        marker.addTo(planeLayer);

        marker.on('click', (ev) => {
            clear_table();

            // Add plane entries entries; TODO: find a better way to do this
            $("#infoPane table").append(`<tr><td>ICAO 24-bit Address</td><td>${plane.icao24.toUpperCase()}</td></tr>`);
            $("#infoPane table").append(`<tr><td>Callsign</td><td>${plane.callsign}</td></tr>`);
            $("#infoPane table").append(`<tr><td>Country Origin</td><td>${plane.origin_country}</td></tr>`);
            $("#infoPane table").append(`<tr><td>Time of Last Position Report</td><td>${Date(plane.time_position)}</td></tr>`);
            $("#infoPane table").append(`<tr><td>Last Contact (time)</td><td>${Date(plane.last_contact)}</td></tr>`);
            $("#infoPane table").append(`<tr><td>Position (Latitude, Longitude)</td><td>${plane.latitude}\u00b0N ${plane.longitude}\u00b0W</td></tr>`);
            $("#infoPane table").append(`<tr><td>Geometric Altitude (m)</td><td>${plane.geo_altitude}</td></tr>`);
            $("#infoPane table").append(`<tr><td>On Ground?</td><td>${plane.on_ground ? "Yes" : "No"}</td></tr>`);
            $("#infoPane table").append(`<tr><td>Velocity (m/s)</td><td>${plane.velocity}</td></tr>`);
            $("#infoPane table").append(`<tr><td>Heading (True Track, in degrees)</td><td>${plane.true_track}</td></tr>`);
            $("#infoPane table").append(`<tr><td>Vertical Rate (m/s)</td><td>${plane.vertical_rate}</td></tr>`);
            $("#infoPane table").append(`<tr><td>Squawk</td><td>${plane.squawk}</td></tr>`);
            $("#infoPane table").append(`<tr><td>Position Source</td><td>${get_position_source_string(plane.position_source)}</td></tr>`);
            $("#infoPane table").append(`<tr><td>Plane Category</td><td>${get_plane_category_string(plane.category)}</td></tr>`);

            draw_flight_path(plane.icao24);

            // Hide zoom controls (draws over top of the table)
            $(".leaflet-control-zoom").hide();

            // Display data
            $("#infoPane").show();
        });
    }
}

function draw_airport_markers(airport_data) {
    // TODO: combine airport and plane marker draw functions into one function
    airportLayer.clearLayers();

    for (const airport of airport_data) {
        let marker = L.marker([airport.latitude, airport.longitude]);
        marker.setIcon(airportIcon);
        marker.addTo(airportLayer);

        marker.on('click', (event) => {
            clear_table();

            $("#infoPane table").append(`<tr><td>Identifier</td><td>${airport.ident}</td></tr>`);
            $("#infoPane table").append(`<tr><td>Name</td><td>${airport.name}</td></tr>`);
            $("#infoPane table").append(`<tr><td>Position (Latitude, Longitude)</td><td>${airport.latitude}\u00b0N ${airport.longitude}\u00b0W</td></tr>`);
            $("#infoPane table").append(`<tr><td>Elevation</td><td>${airport.elevation} feet</td></tr>`);
            $("#infoPane table").append(`<tr><td>Region Name</td><td>${airport.region_name}</td></tr>`);
            $("#infoPane table").append(`<tr><td>Municipality</td><td>${airport.municipality}</td></tr>`);
            $("#infoPane table").append(`<tr><td>GPS Code</td><td>${airport.gps_code}</td></tr>`);
            $("#infoPane table").append(`<tr><td>IATA Code</td><td>${airport.iata_code}</td></tr>`);
            $("#infoPane table").append(`<tr><td>Local Code</td><td>${airport.local_code}</td></tr>`);
            $("#infoPane table").append(`<tr><td>Website</td><td>${airport.home_link}</td></tr>`);

            // Hide zoom controls (draws over top of the table)
            $(".leaflet-control-zoom").hide();

            // Display data
            $("#infoPane").show();
        });
    }
}

function main() {
    // Event listener for clicking on the close button
    $("#closeButton").on('click', (event) => {
        // Hide table
        $("#infoPane").hide();
        // Redraw zoom controls
        $(".leaflet-control-zoom").show();
    });

    // Clears and redraws icons when a map zoom event fires.
    // This is to address an issue where the placement of the icons becomes less accurate the further in the map zooms.
    map.on('zoom', function (event) {
        planeLayer.clearLayers();
        flightPathLayer.clearLayers();

        draw_plane_markers(planeData);
    });

    // create http request object
    const plane_data_request = new XMLHttpRequest();

    // add event listener for when a plane data response is received
    plane_data_request.addEventListener("load", () => {
        // ignore cases where response body is null
        if (plane_data_request.response == null)
            return;

        planeData = plane_data_request.response.plane_data;
        draw_plane_markers(plane_data_request.response.plane_data);
    });

    // Create a GET request to send to the plane_states endpoint
    plane_data_request.open("GET", "/data/plane_states");
    // Specify a JSON return type
    plane_data_request.responseType = "json";
    // Send request
    plane_data_request.send();
}