import os
import time

CACHE_DIR = "models_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def model_path_for(ticker: str) -> str:
    safe = ticker.replace("/", "_")
    return os.path.join(CACHE_DIR, f"{safe}.h5")

def scaler_path_for(ticker: str) -> str:
    safe = ticker.replace("/", "_")
    return os.path.join(CACHE_DIR, f"{safe}_scaler.pkl")

def is_model_recent(ticker: str, max_age_hours: int = 24) -> bool:
    path = model_path_for(ticker)
    if not os.path.exists(path):
        return False
    mtime = os.path.getmtime(path)
    return (time.time() - mtime) < (max_age_hours * 3600)
