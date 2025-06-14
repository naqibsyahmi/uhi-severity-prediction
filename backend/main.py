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
from geopy.distance import geodesic
import os

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

    file_path = os.path.join("data", "Training_data_uhi_index_UHI2025-v2.csv")

    ground_uhi_df = pd.read_csv(file_path)
    ground_uhi_df['datetime'] = pd.to_datetime(ground_uhi_df['datetime'], dayfirst=True)

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

    hourly_data = pd.DataFrame({
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
        "shortwave_radiation_instant": hourly.Variables(2).ValuesAsNumpy()
    })

    def map_ground_data(ground_uhi_df, ground_combined_df, tolerance_minutes=60, max_distance_meters=7000):
        ground_combined_df = ground_combined_df.copy()
        matched_rows = []

        for _, uhi_row in tqdm(ground_uhi_df.iterrows(), total=len(ground_uhi_df), desc="Mapping ground data"):

            uhi_time = uhi_row['datetime']

            # Make both datetime timezone-naive
            ground_combined_df['datetime'] = ground_combined_df['datetime'].dt.tz_localize(None)
            uhi_time = uhi_time
            
            uhi_lat = uhi_row['Latitude']
            uhi_lon = uhi_row['Longitude']

            ground_combined_df['time_difference'] = (ground_combined_df['datetime'] - uhi_time).abs()
            window = pd.Timedelta(minutes=tolerance_minutes)
            time_candidates = ground_combined_df[ground_combined_df['time_difference'] <= window]

            if not time_candidates.empty:
                time_candidates = time_candidates.copy()
                time_candidates['distance'] = time_candidates.apply(lambda row: geodesic((uhi_lat, uhi_lon), (row['latitude'], row['longitude'])).meters, axis=1)
                spatial_candidates = time_candidates[time_candidates['distance'] <= max_distance_meters]
                if not spatial_candidates.empty:
                    best_match = spatial_candidates.loc[spatial_candidates['time_difference'].idxmin()]
                    matched_rows.append(best_match.drop(labels=['distance', 'time_difference']))
                    continue

            matched_rows.append(pd.Series([np.nan] * len(ground_combined_df.columns), index=ground_combined_df.columns))

        matched_df = pd.DataFrame(matched_rows).reset_index(drop=True)
        combined = pd.concat([ground_uhi_df.reset_index(drop=True), matched_df], axis=1)
        return combined

    mapped_ground_df = map_ground_data(ground_uhi_df, hourly_data)

    lower_left = (features.latitude - 0.03, features.longitude - 0.07)
    upper_right = (features.latitude + 0.03, features.longitude + 0.07)
    bounds = (lower_left[1], lower_left[0], upper_right[1], upper_right[0])
    time_window = f"{start_date}T00:00:00Z/{end_date}T23:59:59Z"

    stac = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")

    # Sentinel-2
    search_sentinel = stac.search(bbox=bounds, datetime=time_window, collections=["sentinel-2-l2a"], query={"eo:cloud_cover": {"lt": 20}})
    signed_items_sentinel = [planetary_computer.sign(item) for item in search_sentinel.get_items()]

    # Landsat-8
    search_landsat = stac.search(bbox=bounds, datetime=time_window, collections=["landsat-c2-l2"], query={"eo:cloud_cover": {"lt": 20}, "platform": {"in": ["landsat-8"]}})
    signed_items_landsat = [planetary_computer.sign(item) for item in search_landsat.get_items()]

    resolution = 10  # meters per pixel
    scale = resolution / 111320.0  # degrees per pixel

    data_sentinel = stac_load(
        signed_items_sentinel,
        bands=["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"],
        crs="EPSG:4326",
        resolution=scale,
        chunks={"x": 2048, "y": 2048},
        dtype="uint16",
        patch_url=planetary_computer.sign,
        bbox=bounds
    )

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

    scale1, offset1 = 0.0000275, -0.2
    scale2, offset2 = 0.00341802, 149.0
    kelvin_celsius = 273.15
    data1_landsat = data1_landsat.astype(float) * scale1 + offset1
    data2_landsat = data2_landsat.astype(float) * scale2 + offset2 - kelvin_celsius

    median_sentinel = data_sentinel.median(dim="time").compute()
    median_landsat1 = data1_landsat.median(dim="time").compute()
    median_landsat2 = data2_landsat.median(dim="time").compute()
    median_landsat = xr.merge([median_landsat1, median_landsat2])

    def map_satellite_data(median, uhi_df):
        latitudes = uhi_df['Latitude'].values
        longitudes = uhi_df['Longitude'].values
        band_names = list(median.data_vars)
        band_values = {band: [] for band in band_names}

        for lat, lon in tqdm(zip(latitudes, longitudes), total=len(latitudes), desc="Mapping satellite data"):
            for band in band_names:
                value = median[band].sel(latitude=lat, longitude=lon, method='nearest').values.item()
                band_values[band].append(value)
        return pd.DataFrame(band_values)

    sentinel_features = map_satellite_data(median_sentinel, ground_uhi_df)
    landsat_features = map_satellite_data(median_landsat, ground_uhi_df)

    mapped_satellite_combined_df = pd.concat([ground_uhi_df.reset_index(drop=True), sentinel_features, landsat_features], axis=1)
    band_columns = [col for col in mapped_satellite_combined_df.columns if col.startswith('B') or col in ['red', 'green', 'blue', 'nir08', 'swir16', 'swir22', 'lwir11']]
    mapped_satellite_combined_df = mapped_satellite_combined_df.drop_duplicates(subset=band_columns).reset_index(drop=True)

    mapped_ground_df = mapped_ground_df.loc[:, ~mapped_ground_df.columns.duplicated()]
    mapped_satellite_combined_df = mapped_satellite_combined_df.loc[:, ~mapped_satellite_combined_df.columns.duplicated()]
    final_combined_df = pd.merge(mapped_ground_df, mapped_satellite_combined_df, how='inner', on=['Longitude', 'Latitude', 'datetime', 'UHI Index'])

    final_combined_json = final_combined_df.to_json(orient="records", date_format="iso")

    return JSONResponse(content=jsonable_encoder({"final_combined_data": final_combined_json}))
