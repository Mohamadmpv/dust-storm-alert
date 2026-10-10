import requests
from config import API_URL, AIR_QUALITY_URL, FORECAST_DAYS


def get_wind_data(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "forecast_days": FORECAST_DAYS,
        "wind_speed_unit": "kmh",
    }
    try:
        r = requests.get(API_URL, params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Wind API error:", e)
        return None


def get_dust_data(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "pm10,dust",
        "forecast_days": FORECAST_DAYS,
    }
    try:
        r = requests.get(AIR_QUALITY_URL, params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Dust API error:", e)
        return None

def get_wind_data_high_alt(lat, lon):
    """دریافت باد در ترازهای بالاتر (برای پیش‌بینی مسیر)"""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_850hPa,wind_direction_850hPa",
        "forecast_days": 2,
        "wind_speed_unit": "kmh",
    }
    try:
        r = requests.get(API_URL, params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("High-alt API error:", e)
        return None