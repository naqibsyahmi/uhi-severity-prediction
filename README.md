# 🏙️🔥 Urban Heat Island (UHI) Severity Prediction

## 📝 Project Overview

### ❗️Problem Statement
1. **Urban areas are getting hotter** compared to rural areas due to the **Urban Heat Island (UHI)**.​

2. **High building density, lack of green spaces,** and **waste heat** from transportation and industries contribute to this matter. ​

3. **Vulnerable groups** such as elderly and children are at higher risk of heat-related health issues. Low-income communities also will have struggles in coping with extreme heat due to limited access to cooling systems, healthcare, and safe living conditions.​

4. **Climate change** and **rapid urbanization** are making the problem even worse.​

5. While current models often **rely on satellite data** to estimate urban temperatures, these models primarily measures **land surface temperature (LST)**, which does not accurately reflect near-surface air temperature—the metric most relevant to human thermal exposure.​

6. There is a **lack of public awareness** and **accessible open-source tools** for city planners to understand and address UHI.​


### 🎯 Project Objectives
1. **To identify** key environmental and structural factors (e.g., vegetation cover, surface temperature, building density) that influence UHI intensity in selected urban areas.

2. **To assess** the health impacts of UHI on vulnerable populations, including the elderly, children, and low-income communities, in the context of urban settings.

3. **To evaluate** the effectiveness of current UHI modeling techniques, particularly those relying on satellite-derived surface temperature data, in accurately representing ground-level air temperatures.

4. **To develop** accessible, open-source tools for city planners and policymakers to better understand and mitigate the effects of UHI.

5. **To propose** sustainable urban planning strategies aimed at reducing UHI intensity, such as increasing green spaces and implementing heat-reflective building materials.

## 🚀 Getting Started

### Preliminaries

1. **Python 3.10+**: Please ensure that Python 3.10 or higher is installed on your system before running this project. You can download the required version from the official website [Install Python](https://www.python.org/downloads/).


### Setting Up the Environment

1. Clone the repository by running the following command in your terminal:
    ```
    https://github.com/naqibsyahmi/uhi-severity-prediction.git
    ```

2. Create a virtual environment named **`venv`** in your project folder by running the following command:
    ```
    python -m venv venv
    ```

3. Activate the virtual environment based on your operating system:

    - **On Windows:**
    ```
    .\\.venv\Scripts\activate
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

2. Run the following command to run the project:

    ```
    jupyter nbconvert --to notebook --execute uhi_severity.ipynb --inplace
    ```

3. Run the following command to run the backend server:

    ```
    uvicorn api:app --reload --app-dir ../backend
    ```

4. Run the following command to run the frontend server:

    ```
    streamlit run app.py
    ```