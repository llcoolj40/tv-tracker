import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import requests

# --- CONFIG ---
# This pulls from your 'Secrets' in Streamlit Cloud
TMDB_TOKEN = st.secrets["tmdb"]["token"]
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
HEADERS = {"Authorization": f"Bearer {TMDB_TOKEN}"}

st.set_page_config(page_title="BingeTracker Elite", page_icon="📺", layout="wide")

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def get_streaming_service(show_id):
    """Fetches where the show is streaming in the US."""
    url = f"https://api.themoviedb.org/3/tv/{show_id}/watch/providers"
    try:
        res = requests.get(url, headers=HEADERS).json()
        results = res.get('results', {}).get('US', {}).get('flatrate', [])
        return results[0]['provider_name'] if results else "Check App"
    except:
        return "Unknown"

def fetch_show_data(query):
    """Searches TMDB for show details."""
    url = f"https://api.themoviedb.org/3/search/tv?query={query}"
    res = requests.get(url, headers=HEADERS).json()
    if res.get('results'):
        top_result = res['results'][0]
        service = get_streaming_service(top_result['id'])
        return {
            "name": top_result['name'],
            "summary": top_result['overview'],
            "poster": f"https://image.tmdb.org/t/p/w500{top_result['poster_path']}",
            "service": service
        }
    return None

# --- APP UI ---
st.title("📺 My iPad Watchlist")

# Load data from Google Sheets
df = conn.read(spreadsheet=SHEET_URL)

# --- SIDEBAR: SEARCH & ADD ---
with st.sidebar:
    st.header("🔍 Find a New Show")
    search_query = st.text_input("Type show name...")
    if search_query:
        data = fetch_show_data(search_query)
        if data:
            st.image(data['poster'], width=150)
            st.write(f"**{data['name']}**")
            st.caption(f"Streaming: {data['service']}")
            if st.button("Add to My List"):
                new_row = pd.DataFrame([{
                    "Show Name": data['name'], 
                    "Season": 1, 
                    "Episode": 1,
                    "Service": data['service'], 
                    "Summary": data['summary'],
                    "Poster": data['poster']
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, data=df)
                st.success("Added! Refreshing...")
                st.rerun()

# --- MAIN VIEW: YOUR SHOW TILES ---
st.divider()

if df.empty or len(df) == 0:
    st.info("Your list is empty! Use the sidebar to search for a show.")
else:
    # Ensure numbers are clean (fixes the float64 error)
    df['Season'] = pd.to_numeric(df['Season']).fillna(1).astype(int)
    df['Episode'] = pd.to_numeric(df['Episode']).fillna(1).astype(int)

    # Create a grid (4 shows per row)
    for i in range(0, len(df), 4):
        cols = st.columns(4)
        for j, col in enumerate(cols):
            if i + j < len(df):
                row = df.iloc[i + j]
                with col:
                    # Poster
                    if pd.notna(row['Poster']):
                        st.image(row['Poster'], use_container_width=True)
                    
                    st.subheader(row['Show Name'])
                    st.caption(f"📍 {row['Service']}")
                    
                    # Trackers
                    new_s = st.number_input("Season", value=int(row['Season']), key=f"s{i+j}", step=1)
                    new_e = st.number_input("Episode", value=int(row['Episode']), key=f"e{i+j}", step=1)
                    
                    if st.button("Update Progress", key=f"btn{i+j}"):
                        df.at[i+j, 'Season'] = new_s
                        df.at[i+j, 'Episode'] = new_e
                        conn.update(spreadsheet=SHEET_URL, data=df)
                        st.toast(f"Saved {row['Show Name']}!")
