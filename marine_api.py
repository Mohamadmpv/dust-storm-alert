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
            minimum_depth=0.5, maximum_depth=1.5, # اصلاح عمق برای همخوانی با دیتاست
            username=COPERNICUS_USER, password=COPERNICUS_PASS
        )
        sst = float(ds["thetao"].mean())
        return round(sst, 1)
    except Exception as e:
        print(f"Copernicus SST Error for {lat},{lon}: {e}")
        return None

def get_copernicus_chlorophyll(lat, lon):
    """دریافت کلروفیل-a از Copernicus (با دیتاست معتبر)"""
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        
        # تغییر دیتاست به یک دیتاست معتبر برای کلروفیل
        ds = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_bgc_anfc_0.25deg_P1D-m", 
            variables=["chl"],
            minimum_longitude=lon - 0.5, maximum_longitude=lon + 0.5,
            minimum_latitude=lat - 0.5, maximum_latitude=lat + 0.5,
            start_datetime=start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            end_datetime=end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            minimum_depth=0.5, maximum_depth=1.5, # اصلاح عمق
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
    if degree is None: return "نامشخص"
    if 337.5 <= degree or degree < 22.5: return "شمال"
    elif 22.5 <= degree < 67.5: return "شمال‌شرق"
    elif 67.5 <= degree < 112.5: return "شرق"
    elif 112.5 <= degree < 157.5: return "جنوب‌شرق"
    elif 157.5 <= degree < 202.5: return "جنوب"
    elif 202.5 <= degree < 247.5: return "جنوب‌غرب"
    elif 247.5 <= degree < 292.5: return "غرب"
    elif 292.5 <= degree < 337.5: return "شمال‌غرب"
    return "نامشخص"

def get_wind_analysis(city_name, degree):
    direction = degree_to_direction(degree)
    if city_name in ["زابل (سیستان)", "زاهدان", "مکران"]:
        if direction in ["شمال", "شمال‌غرب", "غرب"]: return f"از سمت {direction} (منشأ: کویرهای مرکزی ایران)"
        elif direction in ["جنوب", "جنوب‌شرق", "شرق"]: return f"از سمت {direction} (منشأ: بیابان‌های افغانستان و پاکستان)"
    elif city_name in ["اهواز", "بوشهر", "خلیج فارس", "بندرعباس", "بندر ماهشهر", "بندر دیر", "بندر لنگه"]:
        if direction in ["شمال", "شمال‌غرب"]: return f"از سمت {direction} (منشأ: عراق و سوریه)"
        elif direction in ["جنوب", "جنوب‌شرق"]: return f"از سمت {direction} (منشأ: بیابان‌های عربستان)"
        elif direction in ["غرب"]: return f"از سمت {direction} (منشأ: صحرای عربستان)"
    elif city_name == "تهران":
        if direction in ["غرب", "جنوب‌غرب"]: return f"از سمت {direction} (منشأ: کویر مرکزی و دشت‌های غربی)"
    elif city_name in ["چابهار", "جاسک", "کنارک"]:
        if direction in ["جنوب", "جنوب‌غرب"]: return f"از سمت {direction} (منشأ: دریای عمان)"
        elif direction in ["شمال", "شمال‌شرق"]: return f"از سمت {direction} (منشأ: پاکستان)"
    return f"از سمت {direction}"