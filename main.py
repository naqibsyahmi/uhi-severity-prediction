from dotenv import load_dotenv

import time
import threading
import uvicorn
import streamlit.web.cli as stcli
import sys

load_dotenv()

# Start backend
def run_uhi_prediction_backend():
    try:
        uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False, app_dir="backend")
    except Exception as e:
        print(f"[ERROR] Failed to start backend: {e}")

# Start frontend
def run_uhi_prediction_frontend():
    try:
        sys.argv = ["streamlit", "run", "src/app.py"]
        stcli.main()
    except Exception as e:
        print(f"[ERROR] Failed to start frontend: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_uhi_prediction_backend, daemon=True).start()
    time.sleep(3)
    run_uhi_prediction_frontend()