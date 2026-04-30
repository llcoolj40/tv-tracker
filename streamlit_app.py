import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import requests

# --- 1. CONFIG & SECRETS ---
# Ensure these match what you pasted into the Streamlit Cloud "Secrets" box
TMDB_TOKEN = st.secrets["tmdb"]["token"]
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
HEADERS = {"Authorization": f"Bearer {TMDB_TOKEN}"}

st.set_page_config(page_title="BingeTracker Elite", page_icon="📺", layout="wide")

# --- 2. GOOGLE SHEETS CONNECTION ---
# ttl=0 ensures the app always checks for the newest data
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

def get_streaming_service(show_id):
    """Fetches where the show is streaming (US region)."""
    url = f"https://api.themoviedb.org/3/tv/{show_id}/watch/providers"
    try:
        res = requests.get(url, headers=HEADERS).json()
        results = res.get('results', {}).get('US', {}).get('flatrate', [])
        return results[0]['provider_name'] if results else "Check App"
    except:
        return "Unknown"

def fetch_show_data(query):
    """Searches TMDB for show details and metadata."""
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

# --- 3. APP UI ---
st.title("📺 My iPad Watchlist")

# Load existing data from Google Sheets
df = conn.read(spreadsheet=SHEET_URL)

# --- 4. SIDEBAR: SEARCH & ADD ---
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
                # Combine old data with new row and save to Google Sheets
                df = pd.concat([df, new_row], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, data=df)
                st.success(f"Added {data['name']}!")
                st.rerun()

# --- 5. MAIN VIEW: THE VERTICAL LIST ---
st.divider()

if df.empty or len(df) == 0:
    st.info("Your list is empty! Use the sidebar to search for a show.")
else:
    # Clean up numbers to prevent decimals/float errors
    df['Season'] = pd.to_numeric(df['Season']).fillna(1).astype(int)
    df['Episode'] = pd.to_numeric(df['Episode']).fillna(1).astype(int)

    # Loop through each show - Note the indentation here!
    for index, row in df.iterrows():
        # Create a narrow column for image and wide column for info
        col_img, col_info = st.columns([0.5, 4])
        
        with col_img:
            if pd.notna(row['Poster']):
                st.image(row['Poster'], width=100)
        
        with col_info:
            st.subheader(row['Show Name'])
            st.write(f"📍 **Streaming on:** {row['Service']}")
            
            # Create a horizontal row for the inputs and button
            c1, c2, c3 = st.columns([1, 1, 1])
            new_s = c1.number_input("Season", value=int(row['Season']), key=f"s{index}", step=1)
            new_e = c2.number_input("Episode", value=int(row['Episode']), key=f"e{index}", step=1)
            
            if c3.button("Update Progress", key=f"btn{index}"):
                df.at[index, 'Season'] = new_s
                df.at[index, 'Episode'] = new_e
                conn.update(spreadsheet=SHEET_URL, data=df)
                st.toast(f"Saved {row['Show Name']}!")
            
            # Summary dropdown to keep it clean
            with st.expander("Show Description"):
                st.write(row['Summary'])
        
        st.divider()
