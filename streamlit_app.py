import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import requests

# --- CONFIG ---
# This tells the app: "Go look in the vault for a key called 'token' inside the 'tmdb' section."
TMDB_TOKEN = st.secrets["tmdb"]["token"]
HEADERS = {"Authorization": f"Bearer {TMDB_TOKEN}"}
SHEET_URL = "https://docs.google.com/spreadsheets/d/1LEoZ_C61NQz7HrnGn5uZ5ofpYDNUH0kLAaULVtY1O3I/edit"

st.set_page_config(page_title="BingeTracker Elite", page_icon="📺", layout="wide")

# Connect to Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def get_streaming_service(show_id):
    """Fetches the primary streaming service for the show in the US."""
    url = f"https://api.themoviedb.org/3/tv/{show_id}/watch/providers"
    res = requests.get(url, headers=HEADERS).json()
    # Grabbing US providers (you can change 'US' to your country code)
    results = res.get('results', {}).get('US', {}).get('flatrate', [])
    return results[0]['provider_name'] if results else "Unknown / Buy"

def fetch_show_data(query):
    url = f"https://api.themoviedb.org/3/search/tv?query={query}"
    res = requests.get(url, headers=HEADERS).json()
    if res.get('results'):
        top_result = res['results'][0]
        show_id = top_result['id']
        service = get_streaming_service(show_id)
        return {
            "name": top_result['name'],
            "summary": top_result['overview'],
            "poster": f"https://image.tmdb.org/t/p/w500{top_result['poster_path']}",
            "service": service
        }
    return None

# --- UI ---
st.title("📺 My Streaming Tracker")
df = conn.read(spreadsheet=SHEET_URL)

with st.sidebar:
    st.header("🔍 Find & Add")
    search = st.text_input("Search Series")
    if search:
        data = fetch_show_data(search)
        if data:
            st.image(data['poster'], width=100)
            st.write(f"Streaming on: **{data['service']}**")
            if st.button("Add to List"):
                new_row = pd.DataFrame([{
                    "Show Name": data['name'], "Season": 1, "Episode": 1,
                    "Service": data['service'], "Poster": data['poster']
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, data=df)
                st.success("Added!")

# DISPLAY SHOW TILES
if not df.empty:
    for i in range(0, len(df), 4): # 4 shows per row
        cols = st.columns(4)
        for j, col in enumerate(cols):
            if i + j < len(df):
                row = df.iloc[i + j]
                with col:
                    st.image(row['Poster'], use_container_width=True)
                    st.subheader(row['Show Name'])
                    st.caption(f"📍 Streaming on: **{row['Service']}**")
                    
                    # Update Progress
                    s = st.number_input("S", value=int(row['Season']), key=f"s{i+j}")
                    e = st.number_input("E", value=int(row['Episode']), key=f"e{i+j}")
                    
                    if st.button("Update", key=f"upd{i+j}"):
                        df.at[i+j, 'Season'] = s
                        df.at[i+j, 'Episode'] = e
                        conn.update(spreadsheet=SHEET_URL, data=df)
                        st.toast("Progress Saved!")
