from geopy.geocoders import Nominatim
from dotenv import load_dotenv
import datetime
import requests
import os
import streamlit as st
import pydeck as pdk
from src.logger import setup_logger

logger = setup_logger("frontend", "logs/frontend/uhi_frontend.log")

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
    place = st.text_input("📍 Enter a town/city name", value="Bronx, New York")

    # Show location name
    geolocator = Nominatim(user_agent="uhi-app")
    location = geolocator.geocode(place)

    if location:
        lat = location.latitude
        lon = location.longitude
        st.success(f"📌 Location found: **{location.address}**")
        logger.info(f"Location found: {location.address}")

    else:
        lat = lon = None
        st.warning("⚠️ Location not found. Please try another name.")
        logger.warning(f"Location not found for input: {place}")

    # Date range input
    date_range = st.date_input(
        "📅 Select Date Range",
        value=(datetime.date(2025, 1, 1), datetime.date(2025, 1, 7))
    )

with col2:
    if lat and lon:
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


if st.button("🚀 Predict") and lat and lon:
    with st.spinner("Retrieving features and predicting..."):
        start_date, end_date = date_range
        get_features_payload = {
            "latitude": lat,
            "longitude": lon,
            "date_interval": f"{start_date}/{end_date}"
        }

        try:
            logger.info(f"Requesting features for {place} ({lat}, {lon}) from {start_date} to {end_date}")
            response = requests.post(INFERENCE_API_GET_FEATURES, json=get_features_payload)
            logger.info(f"Feature response status code: {response.status_code}")

            if response.status_code == 200:
                features_json = response.json()
                logger.info("Feature extraction successful. Sending data for prediction.")

                predict_response = requests.post(INFERENCE_API_PREDICTION, json=features_json)
                logger.info(f"Prediction response status code: {predict_response.status_code}")

                if predict_response.status_code != 200:
                    st.error(f"Error predicting UHI Index: {predict_response.status_code}")
                    logger.error(f"Prediction failed: {predict_response.status_code}")

                else:
                    uhi_result = predict_response.json()

                    # Calculate UHI severity based on predicted UHI index
                    uhi_index = uhi_result['uhi_index']

                    logger.info(f"Prediction completed successfully. UHI Index: {uhi_index:.4f}")
                    st.success("✅ Prediction completed!")

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
                logger.error("Endpoint not found (404)")

            elif response.status_code == 422:
                st.error(f"❗ Validation error {response.status_code}. Check your request payload.")
                logger.error("Validation error (422). Check request payload.")

            elif response.status_code >= 500:
                error_detail = response.json().get("detail", "No detail provided.")
                st.error(f"❗ Server error {response.status_code} : {error_detail}")
                logger.error(f"Server error {response.status_code}: {error_detail}")

            else:
                st.error(f"❗ Unexpected Error {response.status_code}: {response.text}")
                logger.error(f"Unexpected error {response.status_code}: {response.text}")

        except requests.exceptions.RequestException as e:
            st.error("❗ Network error occurred while connecting to the backend.")
            st.exception(e)
            logger.exception("Network error occurred while connecting to the backend.")