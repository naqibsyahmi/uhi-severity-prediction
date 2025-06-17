from geopy.geocoders import Nominatim
from dotenv import load_dotenv
import datetime
import requests
import os
import streamlit as st
import pydeck as pdk

load_dotenv()

# Backend
INFERENCE_API_GET_FEATURES = os.environ.get("INFERENCE_API_GET_FEATURES")
INFERENCE_API_PREDICTION = os.environ.get("INFERENCE_API_PREDICTION")

st.markdown(
    "<h1 style='text-align: center;'>🏙️🔥 Urban Heat Island (UHI) Prediction</h1>",
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


if st.button("🚀 Predict"):
    with st.spinner("Retrieving features and predicting..."):

        start_date, end_date = date_range
        get_features_payload = {
            "latitude": lat,
            "longitude": lon,
            "date_interval": f"{start_date}/{end_date}"
        }

        try:
            response = requests.post(INFERENCE_API_GET_FEATURES, json=get_features_payload)

            if response.status_code == 200:
                features_json = response.json()

                predict_response = requests.post(INFERENCE_API_PREDICTION, json=features_json)

                if predict_response.status_code != 200:
                    st.error(f"Error predicting UHI Index: {predict_response.status_code}")
                else:
                    uhi_result = predict_response.json()
                    st.success("✅ Prediction completed!")
                    # st.metric("🌡️ Predicted UHI Index", f"{uhi_result['uhi_index']:.4f}")

                    # Calculate UHI severity based on predicted UHI index
                    uhi_index = uhi_result['uhi_index']
                    if uhi_index < 0.50:
                        severity = "🟢 Low"
                        bg_color = "rgba(31, 122, 31, 0.6)"

                    elif 0.50 <= uhi_index < 1.00:
                        severity = "🟡 Moderate"
                        bg_color = "rgba(230, 194, 0, 0.6)"

                    elif 1.00 <= uhi_index < 1.50:
                        severity = "🟠 High"
                        bg_color = "rgba(255, 149, 0, 0.6)"

                    else:
                        severity = "🔴 Very High"
                        bg_color = "rgba(204, 0, 0, 0.6)"

                    # Display UHI index and severity
                    col_pred, col_sev = st.columns([1, 2])
                    with col_pred:
                        st.metric("🌡️ Predicted UHI Index", f"{uhi_result['uhi_index']:.4f}")

                    with col_sev:
                        st.markdown(
                            f"""
                            <div style='padding: 0.8rem 1rem; background-color: {bg_color}; border-radius: 0.5rem; color: white; font-weight: bold;'>
                                UHI Severity Level: {severity}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

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