import streamlit as st
try:
    import valkey
except ImportError:
    import redis as valkey
import mysql.connector
import time
import json
import pandas as pd
import plotly.express as px
import random

# --- CONFIGURATION ---
USE_MOCK_DATA = True  # Set False if you have real DB/Valkey

DB_CONFIG = {'user': 'root', 'password': 'password', 'host': 'localhost', 'database': 'airportdb'}
VALKEY_CONFIG = {'host': 'localhost', 'port': 6379, 'decode_responses': True}

# --- CONNECTIVITY ---
def get_db_connection():
    if USE_MOCK_DATA: return None
    return mysql.connector.connect(**DB_CONFIG)

def get_valkey_connection():
    if USE_MOCK_DATA:
        class MockValkey:
            def get(self, key): return st.session_state.get(f"mock_valkey:{key}", None)
            def setex(self, key, time, value): st.session_state[f"mock_valkey:{key}"] = value
            def delete(self, key): 
                if f"mock_valkey:{key}" in st.session_state: del st.session_state[f"mock_valkey:{key}"]
        return MockValkey()
    return valkey.Redis(**VALKEY_CONFIG)

# --- DATA LOGIC: FLIGHT DETAILS ---
def fetch_flight_db(flight_id):
    start = time.time()
    if USE_MOCK_DATA:
        time.sleep(0.3) # Base latency
        data = {"flight_id": flight_id, "airline": "Lufthansa", "from": "JFK", "to": "FRA", "status": "On Time"}
    else:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT f.flight_id, a.airlinename as airline, f.from_airport_id as `from`, f.to_airport_id as `to`, 'On Time' as status FROM flight f JOIN airline a ON f.airline_id = a.airline_id WHERE f.flight_id = %s", (flight_id,))
        data = cursor.fetchone()
        conn.close()
    return data, (time.time() - start) * 1000

# --- DATA LOGIC: MANIFEST (HEAVY QUERY) ---
def fetch_manifest_db(flight_id):
    """Simulates a heavy JOIN operation to get all passengers"""
    start = time.time()
    
    if USE_MOCK_DATA:
        # Simulate a HEAVY query (longer sleep than simple lookup)
        time.sleep(0.8) 
        # Generate fake passengers
        names = ["Jorge", "Roberto", "Adrian", "Sergio", "Alice", "Bob", "Charlie", "Diana"]
        data = [{"seat": f"{r}A", "name": f"{n} Luna", "class": "Economy"} for r, n in enumerate(names, 1)]
    else:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # A 3-table JOIN: Booking -> Passenger -> Flight
        query = """
            SELECT 
                b.seat, 
                p.firstname, 
                p.lastname, 
                b.price 
            FROM booking b
            JOIN passenger p ON b.passenger_id = p.passenger_id
            WHERE b.flight_id = %s
            ORDER BY b.seat ASC
        """
        cursor.execute(query, (flight_id,))
        data = cursor.fetchall()
        conn.close()

    return data, (time.time() - start) * 1000

# --- CACHE ASIDE WRAPPERS ---
def get_data_cache_aside(key_prefix, id, fetch_func, valkey):
    key = f"{key_prefix}:{id}"
    
    # 1. Try Cache
    start = time.time()
    cached = valkey.get(key)
    if cached:
        return json.loads(cached), (time.time() - start) * 1000, "HIT"
    
    # 2. DB Fallback
    data, db_time = fetch_func(id)
    
    # 3. Populate Cache (if data exists)
    if data:
        valkey.setex(key, 3600, json.dumps(data, default=str))
        
    return data, db_time, "MISS"

# --- STREAMLIT UI ---
st.set_page_config(page_title="Valkey Manifest Demo", layout="wide")
st.title("✈️ AirportDB: Relational Joins vs. Valkey Cache")

if 'history' not in st.session_state: st.session_state.history = []

# Inputs
col_input, col_stats = st.columns([1, 2])
with col_input:
    flight_id = st.number_input("Flight ID", value=115, step=1)
    r = get_valkey_connection()
    
    # ACTION BUTTONS
    if st.button("🔍 Get Flight Details (Simple)", width='stretch'):
        res, lat, stat = get_data_cache_aside("flight", flight_id, fetch_flight_db, r)
        st.session_state.history.append({"Type": "Details", "Latency": lat, "Source": "Valkey" if stat=="HIT" else "MariaDB"})
        if res: st.success(f"Flight {res['from']} -> {res['to']}")
        else: st.error("Not Found")

    if st.button("📋 Get Manifest (Heavy Join)", width='stretch'):
        res, lat, stat = get_data_cache_aside("manifest", flight_id, fetch_manifest_db, r)
        st.session_state.history.append({"Type": "Manifest", "Latency": lat, "Source": "Valkey" if stat=="HIT" else "MariaDB JOIN"})
        
        if res:
            st.info(f"Manifest loaded: {len(res)} passengers")
            st.dataframe(res, hide_index=True)

    if st.button("🗑️ Flush Cache"):
        if USE_MOCK_DATA: st.session_state.clear()
        else: r.flushall()
        st.session_state.history = []
        st.warning("Cache Flushed")

# Visualization
with col_stats:
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        
        # Chart 1: Latency Bar Chart
        fig = px.bar(
            df, x=df.index, y="Latency", color="Source", 
            title="Query Latency (Lower is Better)",
            color_discrete_map={"MariaDB": "#FF4B4B", "MariaDB JOIN": "#8B0000", "Valkey": "#00C805"},
            text_auto='.0f'
        )
        st.plotly_chart(fig, width='stretch')

        # Metrics for the very last action
        last = st.session_state.history[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("Last Action", last['Type'])
        c2.metric("Latency", f"{last['Latency']:.1f} ms")
        c3.metric("Source", last['Source'])