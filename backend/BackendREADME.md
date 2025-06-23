## 🎛️ Preliminaries

1. Navigate to the backend directory:

```
cd backend
```

2. Start the backend server:

- **On Windows:**
```
uvicorn.exe api:app --reload
```

- **On macOS/Linux:**
```
uvicorn api:app --reload
```

By default, the app runs at http://127.0.0.1:8000

# 🛰️ API Endpoints

1. `/get_features_data/`

**Method**: POST

**Description**: Retrieves meteorological and satellite-derived features from **Open-Meteo** and **Planetary Computer APIs** for the specified location and date range.

**Sample Request Body:**
```
{
  "latitude": 40.81310667,
  "longitude": -73.90916667,
  "date_interval": "2021-06-01/2021-09-01"
}
```

**Response:**
```
{
  "Avg_Wind_Speed": ...,
  "Wind_Direction": ...,
  "Solar_Flux": ...,
  "B01": ...,
  "B02": ...,
  "B03": ...,
  "B04": ...,
  "B05": ...,
  "B06": ...,
  "B07": ...,
  "B08": ...,
  "B8A": ...,
  "B11": ...,
  "B12": ...,
  "NDVI_Sentinel": ...,
  "NDBI_Sentinel": ...,
  "NDVI_Landsat": ...,
  "NDBI_Landsat": ...,
  "red": ...,
  "green": ...,
  "blue": ...,
  "nir08": ...,
  "swir16": ...,
  "swir22": ...,
  "lwir11": ...,
  }
```

2. `/predict_uhi_index/`

**Method**: POST

**Description**: Accepts a set of precomputed features and returns the predicted UHI severity index.

**Sample Request Body:**
```
{
  "Avg_Wind_Speed": 11.016733169555664,
  "Wind_Direction": 204.09056091308594,
  "Solar_Flux": 223.62933349609375,
  "B01": 947.4907899275612,
  "B02": 1047.1181681422713,
  "B03": 1185.5127400252961,
  "B04": 1192.1563757617569,
  "B05": 1383.9892951592503,
  "B06": 1754.9859137250394,
  "B07": 1913.4450710973133,
  "B08": 1898.5932543789047,
  "B8A": 1956.5498591468322,
  "B11": 1763.226840673029,
  "B12": 1471.0047286420604,
  "NDVI_Sentinel": 0.14784808202828492,
  "NDBI_Sentinel": -0.05645848564023685,
  "NDVI_Landsat": 0.16704879209787196,
  "NDBI_Landsat": -0.13655285907735376,
  "red": 0.10534649708472273,
  "green": 0.10382510369476068,
  "blue": 0.08410809375359317,
  "nir08": 0.17968681064830783,
  "swir16": 0.1516958485612856,
  "swir22": 0.11734549063134796,
  "lwir11": 36.6446444266813
}
```

**Response:**
```
{
  "uhi_index": ...
}
```