from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
import pandas as pd
import requests_cache
from retry_requests import retry
import openmeteo_requests
import pystac_client
import planetary_computer
from odc.stac import stac_load
import xarray as xr
import numpy as np
from tqdm import tqdm
import joblib
import os

app = FastAPI()

cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

class Features(BaseModel):
    latitude: float
    longitude: float
    date_interval: str  # Format: "YYYY-MM-DD/YYYY-MM-DD"

model_path = os.path.join(os.path.dirname(__file__), 'model', 'u')
model = joblib.load(model_path)

class UHIInput(BaseModel):
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

@app.post("/get_weather_satellite_features/")
def get_weather_satellite_features(features: Features):
    start_date, end_date = features.date_interval.split("/")

    url = "https://archive-api.open-meteo.com/v1/archive"
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

    weather_df = pd.DataFrame({
        "datetime": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ),
        "latitude": features.latitude,
        "longitude": features.longitude,
        "wind_speed_10m": hourly.Variables(0).ValuesAsNumpy(),
        "wind_direction_10m": hourly.Variables(1).ValuesAsNumpy(),
        "solar_flux": hourly.Variables(2).ValuesAsNumpy()
    })

    lower_left = (features.latitude - 0.03, features.longitude - 0.07)
    upper_right = (features.latitude + 0.03, features.longitude + 0.07)
    bounds = (lower_left[1], lower_left[0], upper_right[1], upper_right[0])
    time_window = f"{start_date}T00:00:00Z/{end_date}T23:59:59Z"

    stac = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")

    search_sentinel = stac.search(bbox=bounds, datetime=time_window, collections=["sentinel-2-l2a"], query={"eo:cloud_cover": {"lt": 20}})
    signed_items_sentinel = [planetary_computer.sign(item) for item in search_sentinel.get_items()]

    search_landsat = stac.search(bbox=bounds, datetime=time_window, collections=["landsat-c2-l2"], query={"eo:cloud_cover": {"lt": 20}, "platform": {"in": ["landsat-8"]}})
    signed_items_landsat = [planetary_computer.sign(item) for item in search_landsat.get_items()]

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
        bands=["red", "green", "nir08", "swir16", "swir22"],
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
        # "coordinates": {
        #     "latitude": features.latitude,
        #     "longitude": features.longitude,
        # },
        # "satellite_features": {
        #     "NDVI_Sentinel": float(np.nanmean(NDVI_Sentinel.values)),
        #     "NDBI_Sentinel": float(np.nanmean(NDBI_Sentinel.values)),
        #     "NDVI_Landsat": float(np.nanmean(NDVI_Landsat.values)),
        #     "NDBI_Landsat": float(np.nanmean(NDBI_Landsat.values)),
        #     **{band: float(np.nanmean(median_sentinel[band].values)) for band in median_sentinel.data_vars},
        #     **{band: float(np.nanmean(median_landsat[band].values)) for band in median_landsat.data_vars},
        # },
        # "ground_features": {
        #     "avg_wind_speed": float(weather_df["wind_speed_10m"].mean()),
        #     "avg_wind_direction": float(weather_df["wind_direction_10m"].mean()),
        #     "avg_solar_flux": float(weather_df["solar_flux"].mean()),
        # }
        
        "avg_wind_speed": float(weather_df["wind_speed_10m"].mean()),
        "avg_wind_direction": float(weather_df["wind_direction_10m"].mean()),
        "avg_solar_flux": float(weather_df["solar_flux"].mean()),
        **{band: float(np.nanmean(median_sentinel[band].values)) for band in median_sentinel.data_vars},
        "NDVI_Sentinel": float(np.nanmean(NDVI_Sentinel.values)),
        "NDBI_Sentinel": float(np.nanmean(NDBI_Sentinel.values)),
        "NDVI_Landsat": float(np.nanmean(NDVI_Landsat.values)),
        "NDBI_Landsat": float(np.nanmean(NDBI_Landsat.values)),
        **{band: float(np.nanmean(median_landsat[band].values)) for band in median_landsat.data_vars},
    }

    return JSONResponse(content=jsonable_encoder(response_json))

@app.post("/predict_uhi_index/")
def predict_uhi_index(input: UHIInput):
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
    return {"uhi_index": float(prediction[0])}