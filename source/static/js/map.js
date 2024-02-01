var map = L.map('map').fitWorld();

// Organize different elements into groups (makes it easier to clear and redraw markers on update)
var planeLayer = L.layerGroup().addTo(map).setZIndex(600);          // For plane markers
var airportLayer = L.layerGroup().addTo(map).setZIndex(600);        // For airport markers
var infoLayer = L.layerGroup().addTo(map).setZIndex(800);           // For info pane
var flightPathLayer = L.layerGroup().addTo(map).setZIndex(550);     // For flight path lines

var planeData = [];
var airportData = [];

var callInterval;

var currentMapType = null;
var VFRMapCycle = "20230810";
var mapTiles = {};
var mapTypes = {
    geographic: { maxZoom: 18, defaultZoom: 7 },
    vfrc: { maxZoom: 11, defaultZoom: 7 }, // Has zoom level 12 in some areas
    sectc: { maxZoom: 11, defaultZoom: 7 },
    helic: { maxZoom: 11, defaultZoom: 7 }, // Has zoom level 12 in some areas
    ifrlc: { maxZoom: 11, defaultZoom: 7 },
    ehc: { maxZoom: 10, defaultZoom: 7 }
};

/**
 * Initalizes the map tilesets from OpenStreetMap and VFRMap
 */
function initializeMapTiles() {
    for (var type in mapTypes) {
        var mapLink;
        var mapSettings = {
            attribution: "&copy; <a href='https://vfrmap.com/tos.html'>VFRMap</a> contributors",
            maxZoom: mapTypes[type].maxZoom,
            tms: true
        };
        if (type == "geographic") {
            mapLink = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            mapSettings.attribution = "&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors",
            mapSettings.tms = false
        }
        else {
            mapLink = "https://vfrmap.com/" + VFRMapCycle + "/tiles/" + type + "/{z}/{y}/{x}.jpg"
        }
        mapTiles[type] = L.tileLayer(mapLink, mapSettings);
    }
}

/**
 * Sets the map type to the input map type
 *
 * @param {string} mapType string input corresponding to map type can be "geograpgic", "vfrc", "sectc", "helic", "ifrlc", "ehc"
 * 
 */
function setMapType(mapType) {    
    if (currentMapType != null && mapType != currentMapType) {
        mapTiles[currentMapType].removeFrom(map);
        currentMapType = mapType;
        mapTiles[currentMapType].addTo(map);
    }
    else if (currentMapType == null) {
        currentMapType = mapType;
        mapTiles[currentMapType].addTo(map);
    }
}

/**
 * Initalizes the map with geographical map when the page is loaded
 */
function initializeMap() {
    initializeMapTiles();
    setMapType("geographic");
    tileSetChange("geographic");
}

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
        case 0: source = "ADS-B"; break;
        case 1: source = "ASTERIX"; break;
        case 2: source = "MLAT"; break;
        case 3: source = "FLARM"; break;
        default: source = "N/A";
    }
    return source;
}

/**
 * Clears the table in the info pane in preparation for new data.
 */
function clear_table() {
    // Remove previous data
    $("#infoPane").children().each(function (index) {
        if ($(this).attr("id") != "infoTable" && $(this).attr("id") != "closeButton" && $(this).attr("class") != "INFOPANETEMP") // THIS IS KINDA TERRIBLE we really should just be removing those with a tag instead of everything with not this tag
            $(this).remove();
    });

    $("#infoTable").children().each(function (index) {
        $(this).remove();
    });
}

/**
 * Decodes a plane category from the integer representation (i.e. int -> string)
 *
 * @param {int} category_plane plane category from API endpoint
 * @returns {string} decoded plane category
 */
function get_plane_category_string(category_plane) {
    var category = "";
    switch (category_plane) {
        case 0: category = "No Information"; break;
        case 1: category = "No ADS-B Emitter Category Information"; break;
        case 2: category = "Light"; break;
        case 3: category = "Small"; break;
        case 4: category = "Large"; break;
        case 5: category = "High Vortex Large"; break;
        case 6: category = "Heavy"; break;
        case 7: category = "High Performance"; break;
        case 8: category = "Rotocraft"; break;
        case 9: category = "Glider/Sailplane"; break;
        case 10: category = "Lighter-than-air"; break;
        case 11: category = "Parachutist/Skydiver"; break;
        case 12: category = "Ultralight/Hang-Glider/Paraglider"; break;
        case 13: category = "Reserved"; break;
        case 14: category = "Unmanned Aerial Vehicle"; break;
        case 15: category = "Space/Trans-Atmospheric Vehicle"; break;
        case 16: category = "Surface Vehicle-Emergency Vehicle"; break;
        case 17: category = "Surface Vehicle-Service Vehicle"; break;
        case 18: category = "Point Obstacle"; break;
        case 19: category = "Cluster Obstacle"; break;
        case 20: category = "Line Obstacle"; break;
        default: category = "Unknown Aircraft";
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

        let waypoint_coords = [];
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
                        content: `
                        Time: ${waypoint_time.toLocaleString()}<br />
                        Location: ${waypoint.latitude}\u00b0N ${waypoint.longitude}\u00b0W`
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
        let marker = L.marker([plane.latitude, plane.longitude]);

        if (map.getZoom() < 10) {
            var mapZoomBasedIconSize = (map.getZoom() * 2);
            var mapZoomBasedIconSizeCenter = map.getZoom();
            marker.setIcon(L.icon({ iconUrl: plane.category_icon, iconSize: [mapZoomBasedIconSize, mapZoomBasedIconSize], iconAnchor: [mapZoomBasedIconSizeCenter, mapZoomBasedIconSizeCenter], className: "planeMarker" }));
        }
        else {
            marker.setIcon(L.icon({ iconUrl: plane.category_icon, iconSize: [20, 20], iconAnchor: [10, 10], className: "planeMarker" }));
        }
        
        marker.setRotationAngle(plane.true_track); // Rotate icon to match actual plane heading
        marker.setRotationOrigin('center center') // This is required otherwise the rotation will mess up where planes actually are
        marker.addTo(planeLayer);

        marker.on('mouseover', (event) => { // testing mouseover for future hover for each aircraft
            console.log(`${plane.callsign}`);
        });

        marker.on('click', (event) => {
            clear_table();

            // Change the title text
            $(".infoPaneTitle").text("Aircraft Information");

            // Add airport properties
            $("#infoPane").append(`
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Callsign: </li>
                        <li class="infoPaneData aircraftCallsign">${plane.callsign}</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Position: </li>
                        <li class="infoPaneData aircraftPosition">${plane.latitude}\u00b0N ${plane.longitude}\u00b0W</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">ICAO 24-Bit Address: </li>
                        <li class="infoPaneData aircraftICAO">${plane.icao24.toUpperCase()}</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Origin Country: </li>
                        <li class="infoPaneData aircraftOrigin">${plane.origin_country}</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Time of Last Position Report: </li>
                        <li class="infoPaneData aircraftTimePosition">${Date(plane.time_position)}</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Last Contact: </li>
                        <li class="infoPaneData aircraftLastContact">${Date(plane.last_contact)}</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Geometric Altitude: </li>
                        <li class="infoPaneData aircraftGeoAltitude">${plane.geo_altitude} meters</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">On Ground?: </li>
                        <li class="infoPaneData aircraftGroundStatus">${plane.on_ground ? "Yes" : "No"}</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Velocity: </li>
                        <li class="infoPaneData aircraftVelocity">${plane.velocity} meters per second</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Heading: </li>
                        <li class="infoPaneData aircraftHeading">${plane.true_track}\u00b0</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Vertical Rate: </li>
                        <li class="infoPaneData aircraftVerticalRate">${plane.vertical_rate} meters per second</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Squawk: </li>
                        <li class="infoPaneData aircraftSquawk">${plane.squawk}</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Position Source: </li>
                        <li class="infoPaneData aircraftPositionSource">${get_position_source_string(plane.position_source)}</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Category: </li>
                        <li class="infoPaneData aircraftCategory">${get_plane_category_string(plane.category)}</li>
                    </ul>
                </div>
            `);

            draw_flight_path(plane.icao24);

            // Hide zoom controls and map type selection (draws over top of the table)
            $(".leaflet-control-zoom").hide();
            $(".selectionClusterLocation").hide();

            // Display data
            $("#infoPane").show();
        });
    }
}

/**
 * Draws the airport markers that are fetched from the data API when the app starts.
 * Sets up the callback functions for clicking the icons and populating the info table
 * with whatever data is available.
 *
 * @param {Array} airport_data An array of objects associated with a valid API response
 * from the /data/airports/<state> API endpoint.
 */
function draw_airport_markers(airport_data) {
    // TODO: combine airport and plane marker draw functions into one function
    airportLayer.clearLayers();

    for (const airport of airport_data) {
        let marker = L.marker([airport.latitude, airport.longitude]);

        marker.setIcon(L.icon({ iconUrl: "../static/images/markers/airport.svg", iconSize: [30, 30], iconAnchor: [15, 15], className: "airportMarker" }));
        marker.addTo(airportLayer);

        marker.on('mouseover', (event) => { // testing mouseover for future hover for each airport
            console.log(`${airport.ident} ${airport.name}`);
        });

        marker.on('click', (event) => {
            clear_table();

            // Change the title text
            $(".infoPaneTitle").text("Airport Information");

            // Add airport properties
            $("#infoPane").append(`
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Airport Identifier: </li>
                        <li class="infoPaneData airportIdentifier">${airport.ident}</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Airport Name: </li>
                        <li class="infoPaneData airportName">${airport.name}</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Position: </li>
                        <li class="infoPaneData airportPosition">${airport.latitude}\u00b0N  ${airport.longitude}\u00b0W</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Elevation: </li>
                        <li class="infoPaneData airportElevation">${airport.elevation} Feet</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Region: </li>
                        <li class="infoPaneData airportRegion">${airport.region_name}</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Municipality: </li>
                        <li class="infoPaneData airportMunicipality">${airport.municipality}</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">GPS Code: </li>
                        <li class="infoPaneData airportGPS">${airport.gps_code}</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">IATA Code: </li>
                        <li class="infoPaneData airportIATA">${airport.iata_code}</li>
                    </ul>
                </div>
                <div>
                    <ul class="infoPaneItem">
                        <li class="infoPaneLabel">Local Code: </li>
                        <li class="infoPaneData airportLocal">${airport.local_code}</li>
                    </ul>
                </div>
            `);
            if (airport.home_link != null) { // if the airport doesn't have a website, don't display a website block
                $("#infoPane").append(`
                    <div>
                        <ul class="infoPaneItem">
                            <li class="infoPaneLabel">Website: </li>
                            <li class="infoPaneData airportWebsite"><a href=${airport.home_link}>${airport.name}</a></li>
                        </ul>
                    </div>
                `);
            }

            // If there are airport frequencies available, add them to the info pane
            if (airport.tower_frequencies) {
                // collapsible button to show/hide media players
                const $tower_freq = $(`
                    <button type='button' class='collapsible'>Tower Frequencies</button>
                `);
                // container for the media players and labels
                let $content_div = $("<div class='content'></div>");

                // click event handler for the tower frequency dropdown
                $tower_freq.on("click", () => {
                    // toggle visibility
                    $content_div.toggle();
                    // toggle active class (mostly for visual feedback)
                    $tower_freq.toggleClass("activeTower");
                });

                // place collapsible menu after the airport properties
                //$("#infoTable").after($tower_freq); // InfoTable is being phased out
                
                $("#infoPane").children().last().after($tower_freq); // after the last div for the above block place this

                // 'content' div for the media players after the frequency menus
                $tower_freq.after($content_div);

                for (const frequency of airport.tower_frequencies) {
                    let $audio_figure = $(`
                        <figure>
                            <figcaption>${frequency}</figcaption>
                        </figure>
                    `);

                    $content_div.append($audio_figure);
                    $audio_figure.append(`
                        <audio
                            controls
                            src="https://livetraffic2.near.aero/stream/${airport.ident}_${frequency.replace(".", "")}.mp3"
                        >
                        </audio>
                        <button id="transcribe-${airport.ident}_${frequency.replace(".", "")}">Transcribe</button>
                    `);

                    $(`#transcribe-${airport.ident}_${frequency.replace(".", "")}`).on("click", (event) => {
                        $.ajax({
                            url: "/models/transcribe",
                            method: "POST",
                            contentType: "text/plain",
                            data: `https://livetraffic2.near.aero/stream/${airport.ident}_${frequency.replace(".", "")}.mp3`,
                        }).done(() => {
                            console.log("Done");
                        })
                    });
                }
            }

            // Hide zoom controls and map type selection (draws over top of the table)
            $(".leaflet-control-zoom").hide();
            $(".selectionClusterLocation").hide();

            // Display data
            $("#infoPane").show();
        });
    }
}

/**
 * One-time event listener setup.
 */
function setup_event_listeners() {
    // Event listener for clicking on the close button
    $("#closeButton").on('click', (event) => {
        // Hide table
        $("#infoPane").hide();
        // Redraw zoom and map type selection controls
        $(".leaflet-control-zoom").show();
        $(".selectionClusterLocation").show();
    });

    // Prevent mouse events from interacting with the map below the info panel
    $("#infoPane").on('click', (event) => {
        event.stopImmediatePropagation();
    });

    $("#infoPane").on('dblclick', (event) => {
        event.stopImmediatePropagation();
    });

    // Clears and redraws icons when a map zoom event fires.
    // This is to address an issue where the placement of the icons becomes less accurate the further in the map zooms.
    map.on('zoom', function (event) {
        planeLayer.clearLayers();
        flightPathLayer.clearLayers();
        console.log(map.getZoom());
        if (map.getZoom() > 7) {
            draw_plane_markers(planeData);
        }
    });

    map.on("zoomend", onMapZoomEnd);
    map.on("moveend", onMapMoveEnd);
}

/**
 * Main function that gets called on map startup.
 */
function main() {
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

    plane_data_request.open("GET", "/data/plane_states"); // Create a GET request to send to the plane_states endpoint
    plane_data_request.responseType = "json"; // Specify a JSON return type
    plane_data_request.send(); // Send request
}

function getMapLatLonBounds() { // this function order got fucked up, need to fix mm
    var minLonEast = map.getBounds().getEast();
    var maxLonWest = map.getBounds().getWest();
    var minLatSouth = map.getBounds().getSouth();
    var maxLatNorth = map.getBounds().getNorth();

    //var latLonBounds = [minLonEast, maxLonWest, minLatSouth, maxLatNorth]
    var latLonBounds = [minLatSouth, maxLatNorth, maxLonWest, minLonEast]
    
    //console.log(JSON.stringify({latLonBounds : latLonBounds})); // for debugging purposes
    $.ajax({
        url: '/data/getMapLatLonBounds',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({latLonBounds: latLonBounds}),
//        success: function(response) { console.log(response); },
        error: function(error) {
            console.log(error);
        }
    })
}

function onMapZoomEnd() {
    getMapLatLonBounds();
    checkMapZoomLevel();
}

function onMapMoveEnd() {
    getMapLatLonBounds();
}

function checkMapZoomLevel() {
    // Enable the overlay, we are zoomed too far out
    if (map.getZoom() < 8) {
        document.getElementsByClassName('leaflet-map-pane')[0].style.filter = 'blur(10px)';
        document.getElementById('zoomedTooFarOut').style.display = 'flex';

        clearInterval(callInterval); // clear the current interval we have to stop calling planes
        callInterval = null;
    }
    // Disable the overlay, we are zoomed in enough to load planes
    else {
        document.getElementsByClassName('leaflet-map-pane')[0].style.filter = 'blur(0px)';
        document.getElementById('zoomedTooFarOut').style.display = 'none';

        if (map.getZoom() == 8 && callInterval == null) {
            callInterval = setInterval(main, 30000);
        }
    }
}

function dropDownSelection() {
    var coll = document.getElementsByClassName("mapCollapsible");
    coll[0].classList.toggle("active");
    var content = coll[0].nextElementSibling;
    if (content.style.maxHeight) {
        content.style.maxHeight = null;
    }
    else {
        content.style.maxHeight = content.scrollHeight + "px";
    }
}

var currentMapTilesetSelection = "geographic";

function tileSetChange(mapType) {
    document.getElementById(currentMapTilesetSelection).style.backgroundColor = '';
    document.getElementById(mapType).style.backgroundColor = '#cccccc';
    currentMapTilesetSelection = mapType;
    setMapType(mapType);
}

function toggleAltitudeColors() {
    var toggle = document.getElementsByClassName("altitudeColorButton");
    toggle[0].classList.toggle("toggleActive");

    /* do other stuff to change plane icon color */
}
