from fastapi import FastAPI
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

app = FastAPI()

cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

class Features(BaseModel):
    latitude: float
    longitude: float
    date_interval: str  # Format: "YYYY-MM-DD/YYYY-MM-DD"

@app.post("/get_weather_satellite_full/")
def get_weather_satellite_full(features: Features):
    start_date, end_date = features.date_interval.split("/")

    # Weather data retrieval
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

    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ).strftime("%Y-%m-%dT%H:%M:%SZ").tolist(),
        "wind_speed_10m": hourly.Variables(0).ValuesAsNumpy().tolist(),
        "wind_direction_10m": hourly.Variables(1).ValuesAsNumpy().tolist(),
        "shortwave_radiation_instant": hourly.Variables(2).ValuesAsNumpy().tolist()
    }

    lower_left = (features.latitude - 0.03, features.longitude - 0.07)
    upper_right = (features.latitude + 0.03, features.longitude + 0.07)
    bounds = (lower_left[1], lower_left[0], upper_right[1], upper_right[0])
    time_window = f"{start_date}T00:00:00Z/{end_date}T23:59:59Z"

    stac = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")

    # Sentinel-2 Search
    search_sentinel = stac.search(
        bbox=bounds,
        datetime=time_window,
        collections=["sentinel-2-l2a"],
        query={"eo:cloud_cover": {"lt": 20}},
    )
    items_sentinel = list(search_sentinel.get_items())
    signed_items_sentinel = [planetary_computer.sign(item) for item in items_sentinel]

    # Landsat-8 Search
    search_landsat = stac.search(
        bbox=bounds,
        datetime=time_window,
        collections=["landsat-c2-l2"],
        query={"eo:cloud_cover": {"lt": 20}, "platform": {"in": ["landsat-8"]}},
    )
    items_landsat = list(search_landsat.get_items())
    signed_items_landsat = [planetary_computer.sign(item) for item in items_landsat]

    # STAC_LOAD parameters
    resolution = 10  # meters per pixel
    scale = resolution / 111320.0  # degrees per pixel for EPSG:4326

    # Load Sentinel-2 Bands
    data_sentinel = stac_load(
        signed_items_sentinel,
        bands=["B02", "B03", "B04", "B08"],
        crs="EPSG:4326",
        resolution=scale,
        chunks={"x": 2048, "y": 2048},
        dtype="uint16",
        patch_url=planetary_computer.sign,
        bbox=bounds
    )

    # Load Landsat-8 Bands
    data1_landsat = stac_load(
        signed_items_landsat,
        bands=["red", "green", "blue", "nir08", "swir16", "swir22"],
        crs="EPSG:4326",
        resolution=scale,
        chunks={"x": 2048, "y": 2048},
        dtype="uint16",
        patch_url=planetary_computer.sign,
        bbox=bounds
    )

    data2_landsat = stac_load(
        signed_items_landsat,
        bands=["lwir11"],
        crs="EPSG:4326",
        resolution=scale,
        chunks={"x": 2048, "y": 2048},
        dtype="uint16",
        patch_url=planetary_computer.sign,
        bbox=bounds
    )

    def summarize_dataset(ds: xr.Dataset):
        return {
            "bands": list(ds.data_vars.keys()),
            "dimensions": {dim: int(size) for dim, size in ds.dims.items()},
            "crs": str(ds.rio.crs) if hasattr(ds, 'rio') and hasattr(ds.rio, 'crs') else None
        }

    return {
        "weather": hourly_data,
        "satellite_summary": {
            "sentinel_2": summarize_dataset(data_sentinel),
            "landsat_8_rgb_nir_swir": summarize_dataset(data1_landsat),
            "landsat_8_thermal": summarize_dataset(data2_landsat)
        }
    }
