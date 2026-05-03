import streamlit as st
from supabase import create_client, Client
import requests
import pandas as pd

# --- 1. INITIALIZE ---
URL = st.secrets["supabase"]["url"]
KEY = st.secrets["supabase"]["key"]
TMDB_TOKEN = st.secrets["tmdb"]["token"]
HEADERS = {"Authorization": f"Bearer {TMDB_TOKEN}"}

supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="BingeTracker Pro", page_icon="🚀", layout="wide")

# --- 2. DATA ACTIONS ---
def load_data():
    # Supabase returns data instantly, no cache lag!
    response = supabase.table("watchlist").select("*").execute()
    return pd.DataFrame(response.data)

def fetch_show_data(query):
    url = f"https://api.themoviedb.org/3/search/tv?query={query}"
    res = requests.get(url, headers=HEADERS).json()
    if res.get('results'):
        top = res['results'][0]
        return {
            "show_name": top['name'],
            "summary": top['overview'],
            "poster": f"https://image.tmdb.org/t/p/w500{top['poster_path']}",
            "service": "Streaming" # You can add the service fetcher here later
        }
    return None

# --- 3. APP UI ---
st.title("🚀 BingeTracker Pro")
df = load_data()

# SIDEBAR: SEARCH & ADD
with st.sidebar:
    st.header("🔍 Add New Show")
    query = st.text_input("Find a series...")
    if query:
        data = fetch_show_data(query)
        if data:
            st.image(data['poster'], width=150)
            if st.button("Add to My List"):
                # Insert into Supabase
                supabase.table("watchlist").insert({
                    "show_name": data['show_name'],
                    "season": 1,
                    "episode": 1,
                    "service": data['service'],
                    "summary": data['summary'],
                    "poster": data['poster']
                }).execute()
                st.success("Added!")
                st.rerun()

# MAIN VIEW: THE LIST
if not df.empty:
    # Sort alphabetically so it doesn't jump around
    df = df.sort_values("show_name")
    
    for index, row in df.iterrows():
        col_img, col_info = st.columns([0.5, 4])
        
        with col_img:
            st.image(row['poster'], width=100)
            
        with col_info:
            st.subheader(row['show_name'])
            
            c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
            new_s = c1.number_input("S", value=int(row['season']), key=f"s{index}")
            new_e = c2.number_input("E", value=int(row['episode']), key=f"e{index}")
            
            # UPDATE BUTTON
            if c3.button("Update", key=f"upd{index}"):
                supabase.table("watchlist").update({
                    "season": new_s, 
                    "episode": new_e
                }).eq("show_name", row['show_name']).execute()
                st.toast("Saved!")
                st.rerun()
                
            # DELETE BUTTON
            if c4.button("🗑️ Delete", key=f"del{index}"):
                supabase.table("watchlist").delete().eq("show_name", row['show_name']).execute()
                st.rerun()
                
            with st.expander("Summary"):
                st.write(row['summary'])
        st.divider()
else:
    st.info("Search and add a show on the left to get started.")
