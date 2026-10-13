"""
گزارش آب‌وهوا + وضعیت گرد و خاک - هر ۱۲ ساعت
"""
import asyncio
import os
import json
import requests
from telegram import Bot
from jalali import now_jalali


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
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
]


def get_all_chat_ids():
    chat_ids = []
    try:
        if GIST_ID and GH_PAT:
            url = "https://api.github.com/gists/" + GIST_ID
            headers = {"Authorization": "token " + GH_PAT}
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            content = r.json()["files"]["users.json"]["content"]
            users = json.loads(content) if content else {}
            for cid in users.keys():
                cid = str(cid).strip()
                if cid and cid not in chat_ids:
                    chat_ids.append(cid)
    except Exception as e:
        print("Gist read error:", e)
    return chat_ids


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
    params = {
        "latitude": lat, "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
        "forecast_days": 2,
        "timezone": "Asia/Tehran",
    }
    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Weather error:", e)
        return None


def get_dust(lat, lon):
    """دریافت گرد و خاک از Open-Meteo Air Quality"""
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "pm10,dust",
        "forecast_days": 2,
        "timezone": "Asia/Tehran",
    }
    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Dust error:", e)
        return None


def build_message():
    msg = "🌤️ **گزارش روزانه** 🌤️\n\n"
    msg += "📅 " + now_jalali() + "\n"
    msg += "━━━━━━━━━━━━━━━\n\n"

    msg += "🌡️ **آب‌وهوای فردا:**\n\n"
    for city in WEATHER_CITIES:
        data = get_weather(city["lat"], city["lon"])
        if not data or "daily" not in data:
            continue
        d = data["daily"]
        if len(d["time"]) < 2:
            continue
        tmax = d["temperature_2m_max"][1]
        tmin = d["temperature_2m_min"][1]
        rain = d["precipitation_sum"][1]
        code = d["weather_code"][1]

        msg += "🔹 **" + city["name"] + "**: " + weather_code_to_text(code) + "\n"
        msg += "   🌡️ " + str(round(tmin, 1)) + "° تا " + str(round(tmax, 1)) + "°\n"
        if rain and rain > 0:
            msg += "   🌧️ بارش: " + str(round(rain, 1)) + " mm\n"
        msg += "\n"

    msg += "━━━━━━━━━━━━━━━\n\n"
    msg += "🌫️ **وضعیت گرد و خاک:**\n\n"

    for city in WEATHER_CITIES:
        dust = get_dust(city["lat"], city["lon"])
        if not dust or "hourly" not in dust:
            continue
        h = dust["hourly"]
        if "dust" not in h or len(h["dust"]) < 1:
            continue
        now_dust = h["dust"][0]
        if now_dust is None:
            continue

        if now_dust < 20:
            status = "پاک ✅"
        elif now_dust < 50:
            status = "متوسط 🟡"
        elif now_dust < 100:
            status = "ناسالم 🟠"
        else:
            status = "خطرناک 🔴"

        msg += "🔹 **" + city["name"] + "**: " + status + " (" + str(round(now_dust, 1)) + " μg/m³)\n"

    msg += "\n━━━━━━━━━━━━━━━\n"
    return msg


async def send_to_all(message):
    bot = Bot(token=TELEGRAM_TOKEN)
    chat_ids = get_all_chat_ids()
    print("Recipients:", len(chat_ids))
    for cid in chat_ids:
        try:
            await bot.send_message(chat_id=cid, text=message)
            print("Sent to:", cid)
        except Exception as e:
            print("Failed:", cid, e)


def main():
    print("=" * 60)
    print("گزارش آب‌وهوا - " + now_jalali())
    print("=" * 60)
    msg = build_message()
    asyncio.run(send_to_all(msg))
    print("Done.")


if __name__ == "__main__":
    main()