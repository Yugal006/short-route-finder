import streamlit as st
import osmnx as ox
import networkx as nx
from geopy.distance import geodesic
from routeback import get_route
import folium
from streamlit_folium import st_folium

# --- Session state initialization ---
# These store the route, graph, and results between Streamlit reruns
if "route" not in st.session_state:
    st.session_state.route = None
if "graph" not in st.session_state:
    st.session_state.graph = None
if "result" not in st.session_state:
    st.session_state.result = None

# --- OSMnx settings ---
ox.settings.use_cache = True       # Cache downloaded map data
ox.settings.log_console = False    # Disable OSMnx logging

# --- Page configuration ---
st.set_page_config(page_title="India Route Planner", layout="wide")  # wide layout = better for mobile

# --- Helper function ---
def route_to_latlon(graph, route):
    """Convert graph nodes to (lat, lon) coordinates for mapping."""
    return [(graph.nodes[n]["y"], graph.nodes[n]["x"]) for n in route]

# --- UI layout using columns ---
# On desktop: left column for inputs, right column for map/results
# On mobile: columns stack vertically automatically
col1, col2 = st.columns([1, 2])

with col1:
    # --- Input widgets ---
    st.title("India Multi-Mode Route Planner")
    st.write("Find shortest route with distance & estimated time")

    origin = st.text_input("Origin", "Panvel")
    destination = st.text_input("Destination", "Juinagar")
    mode_name = st.selectbox("Select Mode", ["Car 🚗", "Walking 🚶", "Train 🚆"])

    # Show speed slider only if Car is selected
    speed = st.slider("Car Speed (km/h)", 10, 120, 30, step=5) if mode_name == "Car 🚗" else None

    mode_map = {"Car 🚗": "drive", "Walking 🚶": "walk", "Train 🚆": "train"}
    mode = mode_map[mode_name]

    # --- Clear previous route if inputs change ---
    # Prevents showing old route when user changes origin/destination/mode
    if ("prev_origin" not in st.session_state or
        st.session_state.prev_origin != origin or
        st.session_state.prev_destination != destination or
        st.session_state.prev_mode != mode_name):
        
        st.session_state.route = None
        st.session_state.graph = None
        st.session_state.result = None

    # Save current inputs for comparison next rerun
    st.session_state.prev_origin = origin
    st.session_state.prev_destination = destination
    st.session_state.prev_mode = mode_name

    # --- Find Route button ---
    if st.button("Find Route"):
        # Clear previous route/result to ensure fresh calculation
        st.session_state.route = None
        st.session_state.graph = None
        st.session_state.result = None

        try:
            with st.spinner("Downloading map data... Please wait..."):
                # 1️⃣ Get coordinates of origin & destination
                orig_coords = ox.geocode(origin + ", India")
                dest_coords = ox.geocode(destination + ", India")

                # 2️⃣ Compute midpoint and radius for graph download
                midpoint = ((orig_coords[0] + dest_coords[0]) / 2,
                            (orig_coords[1] + dest_coords[1]) / 2)
                radius_m = geodesic(orig_coords, dest_coords).meters / 2 + 4500  # add 2 km buffer

                # 3️⃣ Load graph depending on mode
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

                # 4️⃣ Compute route & estimated distance/time
                result = get_route(graph, mode, origin, destination, speed)
                if "error" in result:
                    st.error(result["error"])
                    st.stop()

                # 5️⃣ Compute shortest path in graph
                route = nx.shortest_path(
                    graph,
                    ox.distance.nearest_nodes(graph, orig_coords[1], orig_coords[0]),
                    ox.distance.nearest_nodes(graph, dest_coords[1], dest_coords[0]),
                    weight="length"
                )

                # 6️⃣ Save route, graph, result in session state
                st.session_state.route = route
                st.session_state.graph = graph
                st.session_state.result = result

        except Exception as e:
            st.error(str(e))

with col2:
    # --- Display route map and results ---
    if st.session_state.route:
        route = st.session_state.route
        graph = st.session_state.graph
        result = st.session_state.result

        # Extract distances and times
        total_distance_km = result["distance"]
        straight_distance = result["straight"]
        total_time_minutes = result["time"]
        hours = int(total_time_minutes // 60)
        minutes = int(total_time_minutes % 60)

        # Display route information
        st.success("Route Calculated Successfully!")
        st.write(f"### 🚦 Mode: {mode_name}")
        if speed:
            st.write(f"🚗 Assumed Speed: {speed} km/h")
        st.write(f"📏 Route Distance: {total_distance_km:.2f} km")
        st.write(f"📐 Straight Distance: {straight_distance:.2f} km")
        st.write(f"⏱ Estimated Time: {hours}h {minutes}m")

        # Convert route to lat/lon for mapping
        route_coords = route_to_latlon(graph, route)
        center = route_coords[len(route_coords)//2] if route_coords else orig_coords

        # --- Folium map ---
        m = folium.Map(location=center, zoom_start=13)
        folium.PolyLine(route_coords, weight=6, color="blue").add_to(m)
        folium.Marker(route_coords[0], tooltip="Origin").add_to(m)
        folium.Marker(route_coords[-1], tooltip="Destination").add_to(m)
        
        # Responsive map: width stretches to container (100%) and reasonable height

        st_folium(m, width="100%", height=400)

