# 🏙️🔥 Urban Heat Island (UHI) Severity Prediction

## 📝 Project Overview

This project was originally developed as part of the **2025 EY Open Science AI & Data Challenge**, an annual global initiative that invites career professionals and students to harness data and AI to address urgent climate issues.

The 2025 challenge focused on the **Urban Heat Island (UHI)** effect, a phenomenon where urban areas experience significantly higher temperatures than surrounding rural zones, posing serious health and environmental risks. Participants were tasked with building machine learning models to predict the severity of UHI hotspots using multisource geospatial and meterorological data. 

Participants were provided with training datasets specific to **New York City**, including:

- Urban near-surface air temperature data for selected boroughs (Manhattan and the Bronx).

- Access to satellite-based Earth observation data via the Microsoft Planetary Computer API.

This repository presents a **full-stack solution** that:

- Predicts UHI severity using regression models trained on ground-based air temperature, satellite-derived imagery, and local weather data.

- Offers an interactive web interface for users to select any urban location, choose a date range, and receive real-time UHI severity.

- Aims to support urban planners, policymakers, and the public in identifying at-risk areas and driving informed decisions for urban sustainability.

### ❗️Problem Statement
1. **Urban areas are getting hotter** compared to rural areas due to the **Urban Heat Island (UHI)**.​

2. **High building density, lack of green spaces,** and **waste heat** from transportation and industries contribute to this matter. ​

3. **Climate change** and **rapid urbanization** are making the problem even worse.​

4. While current models often **rely on satellite data** to estimate urban temperatures, these models primarily measures **land surface temperature (LST)**, which does not accurately reflect near-surface air temperature—the metric most relevant to human thermal exposure.​

5. There is a **lack of public awareness** and **accessible open-source tools** for city planners to understand and address UHI.​


### 🎯 Project Objectives
1. **To identify** key environmental and structural factors (e.g., vegetation cover, surface temperature, building density) that influence UHI intensity in selected urban areas.

2. **To evaluate** the effectiveness of current UHI modeling techniques, particularly those relying on satellite-derived surface temperature data, in accurately representing ground-level air temperatures.

3. **To develop** accessible, open-source tools for city planners and policymakers to better understand and mitigate the effects of UHI.

4. **To propose** sustainable urban planning strategies aimed at reducing UHI intensity, such as increasing green spaces and implementing heat-reflective building materials.


### 🔍 Limitations
1. **Limited geographic scope**: Data extraction focused only on Manhattan and the Bronx, reducing generalizability.

2. **Inconsistent satellite coverage**: Some dates and cities lacked satellite imagery from the satellite data providers, limiting coverage.

3. **Gaps in prediction coverage**: Unavailable satellite imagery during specific periods from providers limited prediction capability.

4. **Temporal limitation**: Model evaluated using date ranges instead of daily granularity, affecting precision.


### 🔮 Future Work
1. **Geographic expansion**: Analyze more cities across diverse climates for broader insights.

2. **Higher-resolution data**: User finer and more frequent satellite imagery to boost accuracy.

3. **UI/UX improvements**: Enhance the tool's interface for better usability.

## 🚀 Getting Started

### Preliminaries

1. **Python 3.10+**: Please ensure that Python 3.10 or higher is installed on your system before running this project. You can download the required version from the official website [Install Python](https://www.python.org/downloads/).


### Setting Up the Environment

1. Clone the repository by running the following command in your terminal:
    ```
    https://github.com/naqibsyahmi/uhi-severity-prediction.git
    ```

2. Create a virtual environment named **`venv`** in your project folder by running the following command:

    - **On Windows:**
    ```
    python -m venv venv
    ```

    - **On macOS/Linux:**
    ```
    python3 -m venv venv
    ```

3. Activate the virtual environment based on your operating system:

    - **On Windows:**
    ```
    venv\Scripts\activate
    ```

    - **On macOS/Linux:**
    ```
    source venv/bin/activate
    ```

4. Once the virtual environment is successfully created and activated, run the following command in your terminal to install the required packages:

    - **On Windows:**
    ```
    pip install -r requirements.txt
    ```

    - **On macOS/Linux:**
    ```
    pip3 install -r requirements.txt
    ```

### Running the System

1. Navigate to the **`src`** folder by running the following command in your terminal:

    ```
    cd src
    ```

2. Run the following command to execute the notebook that trains the prediction model and saves the model file:

    ```
    jupyter nbconvert --to notebook --execute uhi_severity.ipynb --inplace
    ```

3. Once the model is created and and saved in the **`model`** directory, navigate to the project root
    
   If you're current in the `src/` directory, move back to the root:

   ```
   cd ..
   ```

4. Create a **`.env`** file in the root directory

   Add the following environment variables:

   ```
   # Backend
   INFERENCE_API_GET_FEATURES = "http://127.0.0.1:8000/get_features_data"
   INFERENCE_API_PREDICTION = "http://127.0.0.1:8000/predict_uhi_index"  
   ```

5. Once the .env is created, run the following command to run the system:

    ```
    python main.py
    ```