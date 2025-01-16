import streamlit as st
import pandas as pd
import plotly.express as px
import plotly as pl
from datetime import datetime
import pytz

# Initial setup
st.set_page_config(page_title="CMS Performance Dashboard", layout="wide")
st.title("CMS Performance Dashboard")

# Define consistent color scheme
COLOR_SCHEME = px.colors.qualitative.Set3

# Add timestamp
mexico_tz = pytz.timezone('America/Mexico_City')
current_time = datetime.now(mexico_tz)
st.caption(f"Last Updated: {current_time.strftime('%Y-%m-%d %I:%M %p %Z')}")

# Single refresh button
if st.button("🔄 Refresh Data", key="refresh_data_top"):
    st.cache_data.clear()
    st.rerun()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_base_data():
    try:
        doctor_data = pd.read_excel("base_data.xlsx")
        doctor_data['TRANSFORMED DATE'] = pd.to_datetime(
            doctor_data['TRANSFORMED DATE'], 
            dayfirst=True,
            format='%d/%m/%Y'
        )
        doctor_data['Month'] = doctor_data['TRANSFORMED DATE'].dt.to_period('M').astype(str)
        return doctor_data
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

@st.cache_data
def load_top_200_docs():
    try:
        top_200 = pd.read_excel("Top_200_doctores.xlsx")
        responsible_column = None
        possible_names = ['RESPONSABLE', 'Responsable', 'RESPONSIBLE', 'Responsible']
        
        for name in possible_names:
            if name in top_200.columns:
                responsible_column = name
                break
        
        if responsible_column is None:
            st.error("Could not find the responsible person column in the Top 200 Doctors file.")
            return None, None
        
        return top_200, responsible_column
    except Exception as e:
        st.error(f"Error loading Top 200 Doctors file: {str(e)}")
        return None, None

# Load data
base_data = load_base_data()
top_200_docs, responsible_column = load_top_200_docs()

if base_data is not None:
    # Pre-calculate working days data
    working_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    working_data = base_data[base_data['TRANSFORMED DATE'].dt.day_name().isin(working_days)].copy()
    
    # Create single set of tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "One Month Overview", 
        "Two Month Comparison", 
        "Top 200 Doctors Performance",
        "Top 200 Doctors Category Analysis"
    ])
