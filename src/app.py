#.\venv\Scripts\Activate.ps1

import datetime
import requests
import streamlit as st
import joblib
import numpy as np
from geopy.geocoders import Nominatim
import pydeck as pdk

BACKEND_URL = "http://127.0.0.1:8000"

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
    with st.spinner("Retrieving features and predicting..."):

        start_date, end_date = date_range
        get_features_payload = {
            "latitude": lat,
            "longitude": lon,
            "date_interval": f"{start_date}/{end_date}"
        }

        try:
            response = requests.post(f"{BACKEND_URL}/get_features_data/", json=get_features_payload)

            if response.status_code == 200:
                features_json = response.json()

                predict_response = requests.post(f"{BACKEND_URL}/predict_uhi_index/", json=features_json)

                if predict_response.status_code != 200:
                    st.error(f"Error predicting UHI Index: {predict_response.status_code}")
                else:
                    uhi_result = predict_response.json()
                    st.success("✅ Prediction completed!")
                    st.metric("🌡️ Predicted UHI Index", f"{uhi_result['uhi_index']:.4f}")

            elif response.status_code == 404:
                st.error(f"❗ Endpoint not found {response.status_code}. Check your BACKEND_URL.")
            elif response.status_code == 422:
                st.error(f"❗ Validation error {response.status_code}. Check your request payload.")
            elif response.status_code >= 500:
                error_detail = response.json().get("detail", "No detail provided.")
                st.error(f"❗ Server error {response.status_code} : {error_detail}")
            else:
                st.error(f"❗ Unexpected Error {response.status_code}: {response.text}")

        except requests.exceptions.RequestException as e:
            st.error("❗ Network error occurred while connecting to the backend.")
            st.exception(e)
