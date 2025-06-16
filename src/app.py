#.\venv\Scripts\Activate.ps1

import datetime
import streamlit as st
import joblib
import numpy as np
from geopy.geocoders import Nominatim
import pydeck as pdk


model, feature_names = joblib.load("model_with_features.pkl")

st.markdown(
    "<h1 style='text-align: center;'>📍🌡️ UHI Prediction Based on Coordinates</h1>",
    unsafe_allow_html=True
)

col1, col2 = st.columns([1, 1])

with col1:
    lat = st.number_input("📌 Latitude", value=40.812777, format="%.6f")
    lon = st.number_input("📌 Longitude", value=-73.909280, format="%.6f")
    # Show location name
    geolocator = Nominatim(user_agent="uhi-app")
    location = geolocator.reverse((lat, lon), language='en')
    if location:
        st.write(f"📍 Location Name:")
        st.write(f"**{location.address}**")
    else:
        st.warning("Location name not found.")
    # Date range input
    date_range = st.date_input(
        "📅 Select Date Range",
        value=(datetime.date(2025, 1, 1), datetime.date(2025, 1, 7))
    )

with col2:
    satellite_map = pdk.Deck(
        map_style="mapbox://styles/mapbox/satellite-streets-v11",  # <— Satellite style
        initial_view_state=pdk.ViewState(
            latitude=lat,
            longitude=lon,
            zoom=14,
            pitch=45,
        ),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=[{"position": [lon, lat]}],
                get_position="position",
                get_color=[255, 0, 0],
                get_radius=100,
            )
        ],
    )

    st.pydeck_chart(satellite_map)


def extract_features_from_coordinates(lat, lon):
    return np.array([lat * 0.1 + lon * 0.01 + i * 0.001 for i in range(24)])

if st.button("🚀 Predict"):
    # Predict
    features = extract_features_from_coordinates(lat, lon)
    prediction = model.predict([features])[0]
    st.metric("🌡️ Predicted UHI Index", f"{prediction:.4f}")

