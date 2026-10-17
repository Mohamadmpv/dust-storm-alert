import asyncio
import json
import requests
from telegram import Bot as TelegramBot
from config import BALE_TOKEN, TELEGRAM_TOKEN, GIST_ID, GH_PAT, WEATHER_CITIES
from jalali import now_jalali

WEATHER_CITIES = [
    {"name": "تهران",     "lat": 35.6892, "lon": 51.3890},
    {"name": "تبریز",     "lat": 38.0800, "lon": 46.2919},
    {"name": "اهواز",     "lat": 31.3183, "lon": 48.6706},
    {"name": "اصفهان",    "lat": 32.6546, "lon": 51.6680},
    {"name": "بندرعباس",  "lat": 27.1832, "lon": 56.2666},
    {"name": "بوشهر",     "lat": 28.9234, "lon": 50.8200},
    {"name": "چابهار",    "lat": 25.2900, "lon": 60.6430},
    {"name": "بندر انزلی", "lat": 37.4720, "lon": 49.4630},
]

def get_gist_users(filename):
    url = "https://api.github.com/gists/" + GIST_ID
    headers = {"Authorization": "token " + GH_PAT}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        content = r.json()["files"].get(filename, {}).get("content", "")
        return json.loads(content) if content else {}
    except Exception as e:
        print("Gist error:", e)
        return {}

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
    except Exception as e:
        print("Weather error:", e)
        return None

def get_dust(lat, lon):
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {"latitude": lat, "longitude": lon, "hourly": "pm10,dust", "forecast_days": 2, "timezone": "Asia/Tehran"}
    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Dust error:", e)
        return None

def build_message():
    msg = "🌤️ **گزارش روزانه** 🌤️\n\n📅 " + now_jalali() + "\n━━━━━━━━━━━━━━━\n\n🌡️ **آب‌وهوای فردا:**\n\n"
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

    msg += "━━━━━━━━━━━━━━━\n\n🌫️ **وضعیت گرد و خاک:**\n\n"
    for city in WEATHER_CITIES:
        dust = get_dust(city["lat"], city["lon"])
        if not dust or "hourly" not in dust: continue
        h = dust["hourly"]
        if "dust" not in h or len(h["dust"]) < 1: continue
        now_dust = h["dust"][0]
        if now_dust is None: continue
        status = "پاک ✅" if now_dust < 20 else "متوسط 🟡" if now_dust < 50 else "ناسالم 🟠" if now_dust < 100 else "خطرناک 🔴"
        msg += f"🔹 **{city['name']}**: {status} ({round(now_dust, 1)} μg/m³)\n"
    msg += "\n━━━━━━━━━━━━━━━\n"
    return msg

async def send_telegram(msg):
    users = get_gist_users("telegram_users.json")
    if not users: return
    bot = TelegramBot(token=TELEGRAM_TOKEN)
    print("Telegram recipients:", len(users))
    for cid in users.keys():
        try:
            await bot.send_message(chat_id=cid, text=msg)
            print("  TG Sent:", cid)
        except Exception as e:
            print("  TG Failed:", cid, e)

def send_bale(msg):
    users = get_gist_users("bale_users.json")
    if not users: return
    print("Bale recipients:", len(users))
    print("  Bale Token Check:", "Token is OK" if BALE_TOKEN else "Token is None")
    
    for cid in users.keys():
        if not BALE_TOKEN:
            print("  Bale Failed: Token is None")
            continue
            
        url = f"https://tapi.bale.ai/bot{BALE_TOKEN}/sendMessage"
        try:
            r = requests.post(url, json={"chat_id": cid, "text": msg, "parse_mode": "Markdown"}, timeout=30)
            r.raise_for_status()
            print("  Bale Sent:", cid)
        except Exception as e:
            print("  Bale Failed:", cid, e)

async def main():
    print("=" * 60 + "\nگزارش آب‌وهوا - " + now_jalali() + "\n" + "=" * 60)
    msg = build_message()
    await send_telegram(msg)
    send_bale(msg)
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())