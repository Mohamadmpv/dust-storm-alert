import requests
from config import API_URL, AIR_QUALITY_URL, FORECAST_DAYS


def get_wind_data(lat, lon, retries=3):
    """دریافت داده باد از Open-Meteo با تلاش مجدد"""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "forecast_days": FORECAST_DAYS,
        "wind_speed_unit": "kmh",
    }
    for attempt in range(retries):
        try:
            r = requests.get(API_URL, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print("Wind API error (attempt " + str(attempt + 1) + "):", e)
            if attempt < retries - 1:
                import time
                time.sleep(5)
    return None


def get_dust_data(lat, lon, retries=3):
    """دریافت داده گرد و خاک با تلاش مجدد"""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "pm10,dust",
        "forecast_days": FORECAST_DAYS,
    }
    for attempt in range(retries):
        try:
            r = requests.get(AIR_QUALITY_URL, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print("Dust API error (attempt " + str(attempt + 1) + "):", e)
            if attempt < retries - 1:
                import time
                time.sleep(5)
    return None