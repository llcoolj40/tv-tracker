import streamlit as st
from supabase import create_client, Client
import requests
import pandas as pd

# --- 1. INITIALIZE CONNECTIONS ---
# These pull from your Streamlit Cloud "Secrets"
URL = st.secrets["supabase"]["url"]
KEY = st.secrets["supabase"]["key"]
TMDB_TOKEN = st.secrets["tmdb"]["token"]
HEADERS = {"Authorization": f"Bearer {TMDB_TOKEN}"}

# Initialize Supabase Client
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="BingeTracker Pro", page_icon="🚀", layout="wide")

# --- 2. DATA FUNCTIONS ---

def load_data():
    """Fetches all rows from the Supabase 'watchlist' table."""
    try:
        response = supabase.table("watchlist").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def get_streaming_service(show_id):
    """Fetches the US streaming provider from TMDB."""
    url = f"https://api.themoviedb.org/3/tv/{show_id}/watch/providers"
    try:
        res = requests.get(url, headers=HEADERS).json()
        # Change 'US' to your country code if needed (e.g., 'GB', 'CA')
        results = res.get('results', {}).get('US', {}).get('flatrate', [])
        return results[0]['provider_name'] if results else "Check App"
    except:
        return "Multiple/Other"

def fetch_show_data(query):
    """Searches TMDB for a show and gets its metadata."""
    url = f"https://api.themoviedb.org/3/search/tv?query={query}"
    res = requests.get(url, headers=HEADERS).json()
    if res.get('results'):
        top = res['results'][0]
        service = get_streaming_service(top['id'])
        return {
            "show_name": top['name'],
            "summary": top['overview'],
            "poster": f"https://image.tmdb.org/t/p/w500{top['poster_path']}",
            "service": service
        }
    return None

# --- 3. APP UI LAYOUT ---
st.title("🚀 BingeTracker Pro")
df = load_data()

# --- 4. SIDEBAR: SEARCH & ADD ---
with st.sidebar:
    st.header("🔍 Find a New Show")
    query = st.text_input("Type show name...", placeholder="e.g. Succession")
    
    if query:
        data = fetch_show_data(query)
        if data:
            st.image(data['poster'], width=150)
            st.write(f"**{data['show_name']}**")
            st.caption(f"Streaming on: {data['service']}")
            
            if st.button("Add to My List"):
                # Insert a new row into Supabase
                supabase.table("watchlist").insert({
                    "show_name": data['show_name'],
                    "season": 1,
                    "episode": 1,
                    "service": data['service'],
                    "summary": data['summary'],
                    "poster": data['poster']
                }).execute()
                st.success(f"Added {data['show_name']}!")
                st.rerun()

# --- 5. MAIN VIEW: YOUR WATCHLIST ---
st.divider()

if df.empty:
    st.info("Your watchlist is empty! Search for a show in the sidebar to start tracking.")
else:
    # --- NEW: FILTER SECTION ---
    # Create a list of unique services for the dropdown
    all_services = ["All"] + sorted(df['service'].unique().tolist())
    
    # Place the filter at the top of the main area
    selected_filter = st.selectbox("Filter by Streaming Service:", all_services)

    # Filter the dataframe based on selection
    if selected_filter != "All":
        display_df = df[df['service'] == selected_filter]
    else:
        display_df = df

    # Sort alphabetically
    display_df = display_df.sort_values("show_name")
    
    if display_df.empty:
        st.warning(f"No shows found on {selected_filter}")
    else:
        for index, row in display_df.iterrows():
            # Create columns for iPad-friendly horizontal layout
            col_img, col_info = st.columns([0.6, 4])
            
            with col_img:
                if row['poster']:
                    st.image(row['poster'], width=110)
                
            with col_info:
                st.subheader(row['show_name'])
                st.write(f"📍 **Streaming on:** {row['service']}")
                
                # Interactive controls for progress
                c1, c2, c3, c4 = st.columns([1, 1, 1.2, 1])
                
                new_s = c1.number_input("S", value=int(row['season']), key=f"s{index}", step=1)
                new_e = c2.number_input("E", value=int(row['episode']), key=f"e{index}", step=1)
                
                if c3.button("Update Progress", key=f"upd{index}"):
                    supabase.table("watchlist").update({
                        "season": new_s, 
                        "episode": new_e
                    }).eq("show_name", row['show_name']).execute()
                    st.toast(f"Updated {row['show_name']}!")
                    st.rerun()
                    
                if c4.button("🗑️ Delete", key=f"del{index}"):
                    supabase.table("watchlist").delete().eq("show_name", row['show_name']).execute()
                    st.rerun()
                    
                with st.expander("Show Description"):
                    st.write(row['summary'])
            
            st.divider()
