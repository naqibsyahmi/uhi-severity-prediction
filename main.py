from dotenv import load_dotenv


import subprocess
import webbrowser

load_dotenv()

# Activate backend
uhi_prediction_process = subprocess.Popen(
    ["uvicorn", "api:app", "--reload", "--app-dir", "backend"]
)

# Activate frontend
frontend_process = subprocess.Popen(
    ["streamlit", "run", "src/app.py"]
)

webbrowser.open("http://localhost:8501")