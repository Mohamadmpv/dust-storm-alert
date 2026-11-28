import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# --- تابع دریافت داده‌های موج، دما و باد از Open-Meteo ---
def get_marine_data(lat, lon):
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": lat, 
        "longitude": lon,
        "hourly": "wave_height,wave_direction,wave_period,sea_surface_temperature,ocean_current_velocity,wind_speed_10m,wind_direction_10m",
        "forecast_days": 2, 
        "past_days": 2, 
        "timezone": "Asia/Tehran"
    }
    try: 
        return requests.get(url, params=params, timeout=30).json()
    except: 
        return None

# --- تابع تبدیل درجه به جهت جغرافیایی ---
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

# --- تابع تحلیل منبع باد بر اساس نام شهر و جهت ---
def get_wind_analysis(city_name, degree):
    direction = degree_to_direction(degree)
    
    # برای دریای خزر (شمال ایران)
    if city_name in ["بندر انزلی", "بابلسر", "نوشهر", "چالوس", "آستارا", "گرگان (ساحل)"]:
        if direction in ["شمال", "شمال‌غرب"]: return f"از سمت {direction} (منشأ: روسیه و قفقاز)"
        elif direction in ["جنوب", "جنوب‌شرق"]: return f"از سمت {direction} (منشأ: کوه‌های البرز)"
        elif direction == "غرب": return f"از سمت {direction} (منشأ: اروپا)"

    # برای خلیج فارس (جنوب ایران)
    elif city_name in ["بندرعباس", "بوشهر", "بندر لنگه", "خارک", "بندر ماهشهر", "بندر دیر", "قشم", "کیش", "هرمز", "لارک", "هنگام", "سی‌ری"]:
        if direction in ["شمال", "شمال‌غرب"]: return f"از سمت {direction} (منشأ: عراق و سوریه)"
        elif direction in ["جنوب", "جنوب‌شرق"]: return f"از سمت {direction} (منشأ: بیابان‌های عربستان)"
        elif direction == "غرب": return f"از سمت {direction} (منشأ: صحرای عربستان)"

    # برای دریای عمان (جنوب شرق ایران)
    elif city_name in ["چابهار", "جاسک", "کنارک"]:
        if direction in ["جنوب", "جنوب‌غرب"]: return f"از سمت {direction} (منشأ: دریای عمان)"
        elif direction in ["شمال", "شمال‌شرق"]: return f"از سمت {direction} (منشأ: پاکستان)"
        elif direction == "شرق": return f"از سمت {direction} (منشأ: اقیانوس هند)"

    # برای شهرهای غیرساحلی (مثل تهران، زابل و...)
    elif city_name in ["زابل (سیستان)", "زاهدان", "مکران"]:
        if direction in ["شمال", "شمال‌غرب", "غرب"]: return f"از سمت {direction} (منشأ: کویرهای مرکزی ایران)"
        elif direction in ["جنوب", "جنوب‌شرق", "شرق"]: return f"از سمت {direction} (منشأ: بیابان‌های افغانستان و پاکستان)"
    
    elif city_name == "تهران":
        if direction in ["غرب", "جنوب‌غرب"]: return f"از سمت {direction} (منشأ: کویر مرکزی و دشت‌های غربی)"

    return f"از سمت {direction}"