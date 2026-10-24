import asyncio
import os
import requests
from dotenv import load_dotenv

load_dotenv()

import notifier
from jalali import now_jalali

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BALE_TOKEN = os.getenv("BALE_TOKEN")
GIST_ID = os.getenv("GIST_ID")
GH_PAT = os.getenv("GH_PAT")

# لیست شهرها
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
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {"latitude": lat, "longitude": lon, "hourly": "pm2_5,pm10,nitrogen_dioxide", "forecast_days": 1, "timezone": "Asia/Tehran"}
    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def get_inversion_status(weather_data):
    if not weather_data: return "نامشخص"
    try:
        daily = weather_data.get("daily", {})
        if "temperature_2m_max" in daily and "temperature_2m_min" in daily:
            tmax = daily["temperature_2m_max"][0]
            tmin = daily["temperature_2m_min"][0]
            if tmax is not None and tmin is not None:
                diff = tmax - tmin
                if diff < 8: return "🔴 احتمال بالای وارونگی دما"
                elif diff < 12: return "🟡 احتمال متوسط وارونگی دما"
                else: return "🟢 احتمال کم وارونگی دما"
    except Exception: pass
    return "نامشخص"

def get_pm25_status(pm25):
    if pm25 is None: return "نامشخص"
    if pm25 < 12: return "پاک ✅"
    elif pm25 < 35.5: return "قابل قبول 🟡"
    elif pm25 < 55.5: return "ناسالم برای گروه‌های حساس 🟠"
    elif pm25 < 150.5: return "ناسالم 🔴"
    else: return "بسیار ناسالم ⛔"

def build_message():
    msg = "🌤️ **گزارش روزانه آب‌وهوا و آلودگی هوا** 🌤️\n\n📅 " + now_jalali() + "\n"
    msg += "━━━━━━━━━━━━━━━\n\n"
    
    # 1. آب‌وهوا
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

    # 2. آلودگی هوا (برای همه شهرها)
    msg += "━━━━━━━━━━━━━━━\n\n🏭 **وضعیت آلودگی هوا:**\n\n"
    
    for city in WEATHER_CITIES:
        air = get_air_quality(city["lat"], city["lon"])
        if not air or "hourly" not in air: continue
        
        h = air["hourly"]
        pm25 = h.get("pm2_5", [None])[0]
        
        if pm25 is not None:
            status = get_pm25_status(pm25)
            msg += f"🔹 **{city['name']}**: PM2.5 = {round(pm25, 1)} μg/m³ ({status})\n"
            
            # برای تهران و اهواز جزئیات بیشتر و هشدار
            if city["name"] in ["تهران", "اهواز"]:
                pm10 = h.get("pm10", [None])[0]
                no2 = h.get("nitrogen_dioxide", [None])[0]
                weather = get_weather(city["lat"], city["lon"])
                inversion = get_inversion_status(weather)
                
                if pm10 is not None: msg += f"      PM10: {round(pm10, 1)} μg/m³\n"
                if no2 is not None: msg += f"      NO₂: {round(no2, 1)} μg/m³\n"
                msg += f"      وارونگی دما: {inversion}\n"
                
                if pm25 >= 35.5:
                    msg += "      ⚠️ **هشدار:** هوا برای گروه‌های حساس ناسالم است.\n"
        msg += "\n"

    msg += "━━━━━━━━━━━━━━━\n"
    return msg

async def main():
    print("=" * 60 + "\nگزارش آب‌وهوا و آلودگی - " + now_jalali() + "\n" + "=" * 60)
    msg = build_message()
    print("Sending weather report...")
    await notifier._send_to_all_async(msg)
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())