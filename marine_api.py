import os
import copernicusmarine
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

load_dotenv()

COPERNICUS_USER = os.getenv("COPERNICUS_USER")
COPERNICUS_PASS = os.getenv("COPERNICUS_PASS")

def get_copernicus_sst(lat, lon):
    """دریافت دمای سطح آب از Copernicus"""
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        
        ds = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m",
            variables=["thetao"],
            minimum_longitude=lon - 0.1, maximum_longitude=lon + 0.1,
            minimum_latitude=lat - 0.1, maximum_latitude=lat + 0.1,
            start_datetime=start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            end_datetime=end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            minimum_depth=0, maximum_depth=1,
            username=COPERNICUS_USER, password=COPERNICUS_PASS
        )
        sst = float(ds["thetao"].mean())
        return round(sst, 1)
    except Exception as e:
        print(f"Copernicus SST Error for {lat},{lon}: {e}")
        return None

def get_copernicus_chlorophyll(lat, lon):
    """دریافت کلروفیل-a از Copernicus"""
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        
        ds = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_bgc_anfc_0.25deg_P1D-m", 
            variables=["chl"],
            minimum_longitude=lon - 0.5, maximum_longitude=lon + 0.5,
            minimum_latitude=lat - 0.5, maximum_latitude=lat + 0.5,
            start_datetime=start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            end_datetime=end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            minimum_depth=0, maximum_depth=1,
            username=COPERNICUS_USER, password=COPERNICUS_PASS
        )
        chl = float(ds["chl"].mean())
        return round(chl, 2)
    except Exception as e:
        print(f"Copernicus Chl Error for {lat},{lon}: {e}")
        return None

def get_marine_data(lat, lon):
    """دریافت داده‌های موج، دما و باد از Open-Meteo"""
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "wave_height,wave_direction,wave_period,sea_surface_temperature,ocean_current_velocity,wind_speed_10m,wind_direction_10m",
        "forecast_days": 2, "past_days": 2, "timezone": "Asia/Tehran"
    }
    try: return requests.get(url, params=params, timeout=30).json()
    except: return None

def degree_to_direction(degree):
    """تبدیل درجه به جهت جغرافیایی"""
    if degree is None:
        return "نامشخص"
    if 337.5 <= degree or degree < 22.5:
        return "شمال"
    elif 22.5 <= degree < 67.5:
        return "شمال‌شرق"
    elif 67.5 <= degree < 112.5:
        return "شرق"
    elif 112.5 <= degree < 157.5:
        return "جنوب‌شرق"
    elif 157.5 <= degree < 202.5:
        return "جنوب"
    elif 202.5 <= degree < 247.5:
        return "جنوب‌غرب"
    elif 247.5 <= degree < 292.5:
        return "غرب"
    elif 292.5 <= degree < 337.5:
        return "شمال‌غرب"
    return "نامشخص"