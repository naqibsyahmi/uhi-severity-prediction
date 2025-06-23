from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from odc.stac import stac_load
from pydantic import BaseModel
from retry_requests import retry

import joblib
import numpy as np
import openmeteo_requests
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pandas as pd
import planetary_computer
import pystac_client
import requests_cache
import xarray as xr

from src.logger import setup_logger

app = FastAPI()

logger = setup_logger("backend", os.path.join(os.path.dirname(__file__), "..", "logs", "backend", "uhi_backend.log"))

cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "model", "uhi_prediction.pkl"))
model, feature_names = joblib.load(model_path)

class Features(BaseModel):
    """
    Request model for /get_features_data/ endpoint.

    Attributes:
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.
        date_interval (str): Date interval in the format "YYYY-MM-DD/YYYY-MM-DD".
    """
    latitude: float
    longitude: float
    date_interval: str 

class UHIInput(BaseModel):
    """
    Request model for /predict_uhi_index/ endpoint.

    Contains all input features needed by the model (meteorological and satellite-derived).
    """
    Avg_Wind_Speed: float
    Wind_Direction: float
    Solar_Flux: float

    B01: float
    B02: float
    B03: float
    B04: float
    B05: float
    B06: float
    B07: float
    B08: float
    B8A: float
    B11: float
    B12: float

    NDVI_Sentinel: float
    NDBI_Sentinel: float
    NDVI_Landsat: float
    NDBI_Landsat: float

    red: float
    green: float
    nir08: float
    swir16: float
    swir22: float
    lwir11: float

@app.post("/get_features_data/")
def get_features_data(features: Features) -> JSONResponse:
    """
    Endpoint to retrieve averaged meteorological and satellite-derived features for a given location and date interval.

    Parameters:
        features (Features): Request body containing latitude, longitude, and date interval.

    Returns:
        JSON: A JSON response containing a dictionary of all computed features used for UHI index prediction.

    Raises:
        HTTPException: If there is an error in retrieving or processing the data.
    """
    try:
        start_date, end_date = features.date_interval.split("/")

        url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
        params = {
            "latitude": features.latitude,
            "longitude": features.longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ["wind_speed_10m", "wind_direction_10m", "shortwave_radiation_instant"]
        }
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]
        hourly = response.Hourly()

        if len(hourly.Variables(0).ValuesAsNumpy()) == 0:
            raise ValueError("No hourly data returned for the given parameters.")

        hourly_wind_speed_10m = hourly.Variables(0).ValuesAsNumpy()
        hourly_wind_direction_10m = hourly.Variables(1).ValuesAsNumpy()
        hourly_shortwave_radiation_instant = hourly.Variables(2).ValuesAsNumpy()

        weather_df = pd.DataFrame({
            "date": pd.date_range(
                start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
                end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
                freq = pd.Timedelta(seconds = hourly.Interval()),
                inclusive = "left"
            ),
            "latitude": features.latitude,
            "longitude": features.longitude,
            "wind_speed_10m": hourly_wind_speed_10m,
            "wind_direction_10m": hourly_wind_direction_10m,
            "solar_flux": hourly_shortwave_radiation_instant
        })

        lower_left = (features.latitude - 0.03, features.longitude - 0.07)
        upper_right = (features.latitude + 0.03, features.longitude + 0.07)
        bounds = (lower_left[1], lower_left[0], upper_right[1], upper_right[0])
        time_window = f"{start_date}T00:00:00Z/{end_date}T23:59:59Z"

        stac = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")

        search_sentinel = stac.search(bbox=bounds, datetime=time_window, collections=["sentinel-2-l2a"], query={"eo:cloud_cover": {"lt": 60}})
        signed_items_sentinel = [planetary_computer.sign(item) for item in search_sentinel.get_items()]

        search_landsat = stac.search(bbox=bounds, datetime=time_window, collections=["landsat-c2-l2"], query={"eo:cloud_cover": {"lt": 60}, "platform": {"in": ["landsat-8"]}})
        signed_items_landsat = [planetary_computer.sign(item) for item in search_landsat.get_items()]

        if len(signed_items_sentinel) == 0 or len(signed_items_landsat) == 0:
            raise ValueError("No satellite imagery available for the given date and location.")

        resolution = 10
        scale = resolution / 111320.0

        data_sentinel = stac_load(
            signed_items_sentinel,
            bands=["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"],
            crs="EPSG:4326",
            resolution=scale,
            chunks={"x": 2048, "y": 2048},
            dtype="uint16",
            patch_url=planetary_computer.sign,
            bbox=bounds
        ).compute()

        data1_landsat = stac_load(
            signed_items_landsat,
            bands=["red", "green", "blue", "nir08", "swir16", "swir22"],
            crs="EPSG:4326",
            resolution=scale,
            chunks={"x": 2048, "y": 2048},
            dtype="uint16",
            patch_url=planetary_computer.sign,
            bbox=bounds
        ).compute()

        data2_landsat = stac_load(
            signed_items_landsat,
            bands=["lwir11"],
            crs="EPSG:4326",
            resolution=scale,
            chunks={"x": 2048, "y": 2048},
            dtype="uint16",
            patch_url=planetary_computer.sign,
            bbox=bounds
        ).compute()

        scale1, offset1 = 0.0000275, -0.2
        scale2, offset2 = 0.00341802, 149.0
        kelvin_celsius = 273.15

        data1_landsat = data1_landsat.astype(float) * scale1 + offset1
        data2_landsat = data2_landsat.astype(float) * scale2 + offset2 - kelvin_celsius

        median_sentinel = data_sentinel.median(dim="time")
        median_landsat1 = data1_landsat.median(dim="time")
        median_landsat2 = data2_landsat.median(dim="time")
        median_landsat = xr.merge([median_landsat1, median_landsat2])

        NDVI_Sentinel = (median_sentinel["B08"] - median_sentinel["B04"]) / (median_sentinel["B08"] + median_sentinel["B04"])
        NDBI_Sentinel = (median_sentinel["B11"] - median_sentinel["B08"]) / (median_sentinel["B11"] + median_sentinel["B08"])
        NDVI_Landsat = (median_landsat["nir08"] - median_landsat["red"]) / (median_landsat["nir08"] + median_landsat["red"])
        NDBI_Landsat = (median_landsat["swir16"] - median_landsat["nir08"]) / (median_landsat["swir16"] + median_landsat["nir08"])

        response_json = {
            "Avg_Wind_Speed": float(weather_df["wind_speed_10m"].mean()),
            "Wind_Direction": float(weather_df["wind_direction_10m"].mean()),
            "Solar_Flux": float(weather_df["solar_flux"].mean()),
            **{band: float(np.nanmean(median_sentinel[band].values)) for band in median_sentinel.data_vars},
            "NDVI_Sentinel": float(np.nanmean(NDVI_Sentinel.values)),
            "NDBI_Sentinel": float(np.nanmean(NDBI_Sentinel.values)),
            "NDVI_Landsat": float(np.nanmean(NDVI_Landsat.values)),
            "NDBI_Landsat": float(np.nanmean(NDBI_Landsat.values)),
            **{band: float(np.nanmean(median_landsat[band].values)) for band in median_landsat.data_vars},
        }

        logger.info("Feature data successfully retrieved and processed.")
        return JSONResponse(content=jsonable_encoder(response_json))

    except HTTPException as e:
        logger.error(f"HTTPException {e.status_code}: {e.detail}")
        raise

    except Exception as e:
        logger.error(f"Unexpected error at /get_features_data/: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.post("/predict_uhi_index/")
def predict_uhi_index(input: UHIInput) -> dict:
    """
    Endpoint to predict UHI severity index using provided features.

    Parameters:
        input (UHIInput): Request body containing all features required for UHI index prediction.

    Returns:
        dict: Predicted UHI index (float)

    Raises:
        HTTPException: If there is an error in the prediction process.
    """
    try:
        input_array = np.array([
            input.Avg_Wind_Speed,
            input.Wind_Direction,
            input.Solar_Flux,
            input.B01, input.B02, input.B03, input.B04, input.B05,
            input.B06, input.B07, input.B08, input.B8A,
            input.B11, input.B12,
            input.NDVI_Sentinel, input.NDBI_Sentinel,
            input.NDVI_Landsat, input.NDBI_Landsat,
            input.red, input.green, input.nir08,
            input.swir16, input.swir22, input.lwir11
        ]).reshape(1, -1)

        prediction = model.predict(input_array)
        logger.info(f"Prediction successful: {prediction[0]}")
        return {"uhi_index": float(prediction[0])}
    
    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")