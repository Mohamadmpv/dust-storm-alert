"""
گزارش آب‌وهوای فردا - مستقل (بدون وابستگی به notifier)
"""
import asyncio
import os
import json
import requests
from baleio import Bot
from baleio.client.default import DefaultBotProperties
from baleio.enums import ParseMode
from config import BALE_TOKEN, BALE_CHAT_ID, BALE_CHAT_IDS
from jalali import now_jalali


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

    if BALE_CHAT_IDS:
        for cid in BALE_CHAT_IDS:
            cid = str(cid).strip()
            if cid and cid not in chat_ids:
                chat_ids.append(cid)

    if BALE_CHAT_ID and BALE_CHAT_ID not in chat_ids:
        chat_ids.append(BALE_CHAT_ID)

    print("DEBUG: Total chat_ids =", chat_ids)
    return chat_ids


async def send_to_all(message):
    bot = Bot(
        token=BALE_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    chat_ids = get_all_chat_ids()
    print("Total recipients:", len(chat_ids))
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
            print("Sent to:", chat_id)
        except Exception as e:
            print("Failed:", chat_id, e)
    await bot.session.close()


def get_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
        "forecast_days": 2,
        "timezone": "Asia/Tehran",
    }
    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Weather API error:", e)
        return None


def weather_code_to_text(code):
    if code == 0:
        return "☀️ آفتابی"
    elif code in [1, 2]:
        return "🌤️ کمی ابری"
    elif code == 3:
        return "☁️ ابری"
    elif code in [45, 48]:
        return "🌫️ مه‌آلود"
    elif code in [51, 53, 55]:
        return "🌦️ نم‌نم باران"
    elif code in [61, 63, 65]:
        return "🌧️ بارانی"
    elif code in [71, 73, 75]:
        return "❄️ برفی"
    elif code in [80, 81, 82]:
        return "🌧️ رگبار"
    elif code in [95, 96, 99]:
        return "⛈️ رعد و برق"
    else:
        return "نامشخص"


def build_weather_message():
    msg = "🌤️ **گزارش آب‌وهوای فردا** 🌤️\n\n"
    msg += "📅 " + now_jalali() + "\n"
    msg += "━━━━━━━━━━━━━━━\n\n"

    for city in WEATHER_CITIES:
        data = get_weather(city["lat"], city["lon"])
        if not data or "daily" not in data:
            continue

        daily = data["daily"]
        if len(daily["time"]) < 2:
            continue

        tomorrow_max = daily["temperature_2m_max"][1]
        tomorrow_min = daily["temperature_2m_min"][1]
        tomorrow_rain = daily["precipitation_sum"][1]
        tomorrow_code = daily["weather_code"][1]

        weather_text = weather_code_to_text(tomorrow_code)
        rain_text = ""
        if tomorrow_rain and tomorrow_rain > 0:
            rain_text = "   🌧️ بارش: " + str(round(tomorrow_rain, 1)) + " mm\n"

        msg += "🔹 **" + city["name"] + "**\n"
        msg += "   " + weather_text + "\n"
        msg += "   🌡️ دما: " + str(round(tomorrow_min, 1)) + "° تا " + str(round(tomorrow_max, 1)) + "°\n"
        if rain_text:
            msg += rain_text
        msg += "\n"

    msg += "━━━━━━━━━━━━━━━\n"
    return msg


def send_weather_report():
    print("=" * 60)
    print("گزارش آب‌وهوا - " + now_jalali())
    print("=" * 60)

    msg = build_weather_message()
    print(msg)

    asyncio.run(send_to_all(msg))
    print("Done.")


if __name__ == "__main__":
    send_weather_report()