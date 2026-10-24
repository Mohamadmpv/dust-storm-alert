import asyncio
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

import notifier
from jalali import now_jalali

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BALE_TOKEN = os.getenv("BALE_TOKEN")
GIST_ID = os.getenv("GIST_ID")
GH_PAT = os.getenv("GH_PAT")

WEATHER_CITIES = [
    {"name": "تهران",     "lat": 35.6892, "lon": 51.3890},
    {"name": "تبریز",     "lat": 38.0800, "lon": 46.2919},
    {"name": "اهواز",     "lat": 31.3183, "lon": 48.6706},
    {"name": "اصفهان",    "lat": 32.6546, "lon": 51.6680},
    {"name": "بندرعباس",  "lat": 27.1832, "lon": 56.2666},
    {"name": "بوشهر",     "lat": 28.9234, "lon": 50.8200},
    {"name": "چابهار",    "lat": 25.2900, "lon": 60.6430},
    {"name": "بندر انزلی", "lat": 37.4720, "lon": 49.4630},
    {"name": "زابل (سیستان)", "lat": 31.028, "lon": 61.497},
    {"name": "زاهدان", "lat": 29.496, "lon": 60.862}
]

def weather_code_to_text(code):
    if code == 0: return "☀️ آفتابی"
    if code in [1, 2]: return "🌤️ کمی ابری"
    if code == 3: return "☁️ ابری"
    if code in [45, 48]: return "🌫️ مه‌آلود"
    if code in [51, 53, 55]: return "🌦️ نم‌نم باران"
    if code in [61, 63, 65]: return "🌧️ بارانی"
    if code in [71, 73, 75]: return "❄️ برفی"
    if code in [80, 81, 82]: return "🌧️ رگبار"
    if code in [95, 96, 99]: return "⛈️ رعد و برق"
    return "نامشخص"

def get_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code", "forecast_days": 2, "timezone": "Asia/Tehran"}
    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def get_air_quality(lat, lon):
    """دریافت داده‌های کیفیت هوا (PM2.5, PM10, NO2) از Open-Meteo"""
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "pm2_5,pm10,nitrogen_dioxide",
        "forecast_days": 1,
        "timezone": "Asia/Tehran"
    }
    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def get_inversion_status(weather_data, air_data):
    """
    تشخیص احتمال وارونگی دما:
    اگر دما در ارتفاع بالاتر بیشتر از سطح زمین باشد (یا اختلاف دمای شبانه‌روزی کم و باد کم باشد)
    این یک تخمین ساده است بر اساس داده‌های موجود.
    """
    if not weather_data or not air_data:
        return "نامشخص"
    
    try:
        # بررسی اختلاف دمای شبانه‌روزی (اگر اختلاف کم باشد، احتمال وارونگی بیشتر است)
        daily = weather_data.get("daily", {})
        if "temperature_2m_max" in daily and "temperature_2m_min" in daily:
            tmax = daily["temperature_2m_max"][0]
            tmin = daily["temperature_2m_min"][0]
            if tmax is not None and tmin is not None:
                diff = tmax - tmin
                if diff < 8:
                    return "🔴 احتمال بالای وارونگی دما (اختلاف دمای شبانه‌روزی کم)"
                elif diff < 12:
                    return "🟡 احتمال متوسط وارونگی دما"
                else:
                    return "🟢 احتمال کم وارونگی دما"
    except Exception:
        pass
    return "نامشخص"

def build_message():
    msg = "🌤️ **گزارش روزانه آب‌وهوا و آلودگی هوا** 🌤️\n\n📅 " + now_jalali() + "\n"
    msg += "━━━━━━━━━━━━━━━\n\n"
    
    # بخش آب‌وهوا
    msg += "🌡️ **آب‌وهوای فردا (ایران):**\n\n"
    for city in WEATHER_CITIES:
        data = get_weather(city["lat"], city["lon"])
        if not data or "daily" not in data: continue
        d = data["daily"]
        if len(d["time"]) < 2: continue
        tmax, tmin = d["temperature_2m_max"][1], d["temperature_2m_min"][1]
        rain, code = d["precipitation_sum"][1], d["weather_code"][1]
        msg += f"🔹 **{city['name']}**: {weather_code_to_text(code)}\n   🌡️ {round(tmin, 1)}° تا {round(tmax, 1)}°\n"
        if rain and rain > 0: msg += f"   🌧️ بارش: {round(rain, 1)} mm\n"
        msg += "\n"

    # بخش آلودگی هوا (تمرکز روی تهران)
    msg += "━━━━━━━━━━━━━━━\n\n"
    msg += "🏭 **وضعیت آلودگی هوا (تهران):**\n\n"
    
    tehran_air = get_air_quality(35.6892, 51.3890)
    tehran_weather = get_weather(35.6892, 51.3890)
    
    if tehran_air and "hourly" in tehran_air:
        h = tehran_air["hourly"]
        now_idx = 0  # اولین ساعت (فعلی)
        
        pm25 = h.get("pm2_5", [None])[now_idx]
        pm10 = h.get("pm10", [None])[now_idx]
        no2 = h.get("nitrogen_dioxide", [None])[now_idx]
        
        # تعیین وضعیت PM2.5
        if pm25 is not None:
            if pm25 < 12:
                pm25_status = "پاک ✅"
            elif pm25 < 35.5:
                pm25_status = "قابل قبول 🟡"
            elif pm25 < 55.5:
                pm25_status = "ناسالم برای گروه‌های حساس 🟠"
            elif pm25 < 150.5:
                pm25_status = "ناسالم 🔴"
            else:
                pm25_status = "بسیار ناسالم ⛔"
            msg += f"   🔹 **PM2.5 (ذرات ریز):** {round(pm25, 1)} μg/m³ ({pm25_status})\n"
        
        if pm10 is not None:
            msg += f"   🔹 **PM10 (ذرات معلق):** {round(pm10, 1)} μg/m³\n"
        
        if no2 is not None:
            msg += f"   🔹 **NO₂ (دی‌اکسید نیتروژن):** {round(no2, 1)} μg/m³\n"
        
        # وضعیت وارونگی دما
        inversion = get_inversion_status(tehran_weather, tehran_air)
        msg += f"   🔄 **وضعیت وارونگی دما:** {inversion}\n"
        
        # هشدار مرزی
        if pm25 is not None and pm25 >= 35.5:
            msg += "\n   ⚠️ **هشدار:** کیفیت هوا برای گروه‌های حساس نامناسب است. توصیه می‌شود کودکان، سالمندان و بیماران قلبی-ریوی از تردد غیرضروری پرهیز کنند.\n"
    else:
        msg += "   (داده‌های کیفیت هوا در دسترس نیست)\n"

    msg += "\n━━━━━━━━━━━━━━━\n"
    return msg

async def main():
    print("=" * 60 + "\nگزارش آب‌وهوا و آلودگی - " + now_jalali() + "\n" + "=" * 60)
    
    msg = build_message()
    print("DEBUG: Message built. Length:", len(msg))
    
    await notifier._send_to_all_async(msg)
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())