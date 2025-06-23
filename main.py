from dotenv import load_dotenv

import time
import threading
import uvicorn
import streamlit.web.cli as stcli
import os
import sys
from src.logger import setup_logger

logger = setup_logger("main", "logs/uhi_main.log")

# Start backend
def run_uhi_prediction_backend():
    try:
        logger.info("Starting UHI Prediction backend...")
        uvicorn.run("api:app", host="0.0.0.0", reload=False, app_dir="backend")
    except Exception as e:
        logger.error(f"Failed to start backend: {e}")
        sys.exit(1)

# Start frontend
def run_uhi_prediction_frontend():
    try:
        logger.info("Starting frontend...")
        sys.argv = ["streamlit", "run", "src/app.py"]
        stcli.main()
    except Exception as e:
        logger.error(f"Failed to start frontend: {e}")
        sys.exit(1)

if __name__ == "__main__":
    threading.Thread(target=run_uhi_prediction_backend, daemon=True).start()
    time.sleep(3)
    run_uhi_prediction_frontend()