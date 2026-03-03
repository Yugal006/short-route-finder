import osmnx as ox
import networkx as nx
from geopy.distance import geodesic

ox.settings.use_cache = True
ox.settings.log_console = False

SPEEDS = {
    "drive": 30,
    "walk": 4.5,
    "train": 35
}

def load_road_graph(area, mode):
    return ox.graph_from_address(area, dist=10000, network_type=mode)

def load_train_graph(area):
    return ox.graph_from_place(
        area,
        custom_filter='["railway"~"rail|subway|light_rail|tram"]'
    )

# -------------------- CHANGE --------------------
def calculate_time(distance_km, mode, custom_speed=None, graph=None, route=None):
    if mode == "drive" and custom_speed:
        speed = custom_speed
        return (distance_km / speed) * 60

    if mode == "train":
        # Updated train timing to better match Google Maps
        WAIT = 5              # reduced wait time
        CRUISE_SPEED = 35     # slightly faster
        STATION_SPACING = 2.0 # km avg spacing
        STOP_DELAY = 0.45      # min per stop dwell

        stops = distance_km / STATION_SPACING
        run_time = (distance_km / CRUISE_SPEED) * 60
        stop_time = stops * STOP_DELAY
        return WAIT + run_time + stop_time

    if mode in ["drive", "walk"] and graph is not None and route is not None:
        # Use per-edge speeds if available
        total_time = 0
        for u, v in zip(route[:-1], route[1:]):
            data = graph.get_edge_data(u, v)[0]
            length_km = data["length"] / 1000
            speed_kph = data.get("speed_kph", SPEEDS[mode])
            total_time += (length_km / speed_kph) * 60
        return total_time

    # fallback
    speed = SPEEDS.get(mode, 30)
    return (distance_km / speed) * 60

def get_route(graph, mode, origin, destination, speed=None):

    orig_coords = ox.geocode(origin + ", India")
    dest_coords = ox.geocode(destination + ", India")

    orig_node = ox.distance.nearest_nodes(graph, orig_coords[1], orig_coords[0])
    dest_node = ox.distance.nearest_nodes(graph, dest_coords[1], dest_coords[0])

    try:
        route = nx.shortest_path(graph, orig_node, dest_node, weight="length")
    except nx.NetworkXNoPath:
        return {"error": "No route found"}

    total_distance_m = 0
    for u, v in zip(route[:-1], route[1:]):
        edge_data = graph.get_edge_data(u, v)[0]
        total_distance_m += edge_data["length"]

    total_distance_km = total_distance_m / 1000
    # -------------------- CHANGE --------------------
    total_time_minutes = calculate_time(total_distance_km, mode, speed, graph=graph, route=route)
    # -------------------- END CHANGE --------------------
    straight_distance = geodesic(orig_coords, dest_coords).km

    return {
        "distance": round(total_distance_km, 2),
        "straight": round(straight_distance, 2),
        "time": round(total_time_minutes, 1)

    }
