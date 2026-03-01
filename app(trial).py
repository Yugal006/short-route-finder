import streamlit as st
import osmnx as ox
import networkx as nx
from geopy.distance import geodesic
from routeback import get_route
import folium
from streamlit_folium import st_folium

# --- Session state ---
if "route" not in st.session_state:
    st.session_state.route = None
if "graph" not in st.session_state:
    st.session_state.graph = None
if "result" not in st.session_state:
    st.session_state.result = None

# --- OSMnx settings ---
ox.settings.use_cache = True
ox.settings.log_console = False

# --- Page config ---
st.set_page_config(page_title="India Route Planner", layout="centered")

# --- UI ---
st.title("India Multi-Mode Route Planner")
st.write("Find shortest route with distance & estimated time")

origin = st.text_input("Origin", "Panvel")
destination = st.text_input("Destination", "Juinagar")
mode_name = st.selectbox("Select Mode", ["Car 🚗", "Walking 🚶", "Train 🚆"])
speed = st.slider("Car Speed (km/h)", 10, 120, 30, step=5) if mode_name == "Car 🚗" else None

mode_map = {"Car 🚗": "drive", "Walking 🚶": "walk", "Train 🚆": "train"}
mode = mode_map[mode_name]

def route_to_latlon(graph, route):
    return [(graph.nodes[n]["y"], graph.nodes[n]["x"]) for n in route]

# --- Clear previous route if inputs changed ---
if ("prev_origin" not in st.session_state or
    st.session_state.prev_origin != origin or
    st.session_state.prev_destination != destination or
    st.session_state.prev_mode != mode_name):
    
    st.session_state.route = None
    st.session_state.graph = None
    st.session_state.result = None

st.session_state.prev_origin = origin
st.session_state.prev_destination = destination
st.session_state.prev_mode = mode_name

# --- Find Route button ---
if st.button("Find Route"):
    # Clear previous route/result before calculating new one
    st.session_state.route = None
    st.session_state.graph = None
    st.session_state.result = None

    try:
        with st.spinner("Downloading map data... Please wait..."):
            # 1️⃣ Get coordinates
            orig_coords = ox.geocode(origin + ", India")
            dest_coords = ox.geocode(destination + ", India")

            # 2️⃣ Compute midpoint and radius to cover both points
            midpoint = ((orig_coords[0] + dest_coords[0]) / 2,
                        (orig_coords[1] + dest_coords[1]) / 2)
            radius_m = geodesic(orig_coords, dest_coords).meters / 2 + 2000  # buffer 2 km

            # 3️⃣ Load graph
            if mode_name == "Train 🚆":
                graph = ox.graph_from_point(
                    midpoint,
                    dist=radius_m,
                    custom_filter='["railway"~"rail|subway|light_rail|tram"]'
                )
            else:
                net = "drive" if mode_name == "Car 🚗" else "walk"
                graph = ox.graph_from_point(
                    midpoint,
                    dist=radius_m,
                    network_type=net
                )

            # 4️⃣ Compute route & result
            result = get_route(graph, mode, origin, destination, speed)
            if "error" in result:
                st.error(result["error"])
                st.stop()

            route = nx.shortest_path(
                graph,
                ox.distance.nearest_nodes(graph, orig_coords[1], orig_coords[0]),
                ox.distance.nearest_nodes(graph, dest_coords[1], dest_coords[0]),
                weight="length"
            )

            # 5️⃣ Save to session
            st.session_state.route = route
            st.session_state.graph = graph
            st.session_state.result = result

    except Exception as e:
        st.error(str(e))

# --- Display route ---
if st.session_state.route:
    route = st.session_state.route
    graph = st.session_state.graph
    result = st.session_state.result

    total_distance_km = result["distance"]
    straight_distance = result["straight"]
    total_time_minutes = result["time"]
    hours = int(total_time_minutes // 60)
    minutes = int(total_time_minutes % 60)

    st.success("Route Calculated Successfully!")
    st.write(f"### 🚦 Mode: {mode_name}")
    if speed:
        st.write(f"🚗 Assumed Speed: {speed} km/h")
    st.write(f"📏 Route Distance: {total_distance_km:.2f} km")
    st.write(f"📐 Straight Distance: {straight_distance:.2f} km")
    st.write(f"⏱ Estimated Time: {hours}h {minutes}m")

    route_coords = route_to_latlon(graph, route)
    center = route_coords[len(route_coords)//2] if route_coords else orig_coords

    # --- Folium map ---
    m = folium.Map(location=center, zoom_start=13)
    folium.PolyLine(route_coords, weight=6, color="blue").add_to(m)
    folium.Marker(route_coords[0], tooltip="Origin").add_to(m)
    folium.Marker(route_coords[-1], tooltip="Destination").add_to(m)
    st_folium(m, width=700, height=500)