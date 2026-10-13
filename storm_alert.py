"""
هشدار فوری طوفان - بررسی ۲ ساعت آینده، هر ۱ ساعت
"""
import asyncio
import os
import json
import requests
from telegram import Bot
from datetime import datetime, timezone, timedelta
from jalali import now_jalali


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GIST_ID = os.getenv("GIST_ID")
GH_PAT = os.getenv("GH_PAT")

WIND_SPEED_THRESHOLD = 20

# فقط نقاط حساس (دریاها + بنادر + تهران)
URGENT_POINTS = [
    {"name": "دریای خزر",   "lat": 40.0,    "lon": 51.0,    "type": "internal"},
    {"name": "خلیج فارس",   "lat": 27.0,    "lon": 51.0,    "type": "internal"},
    {"name": "دریای عمان",  "lat": 25.0,    "lon": 58.0,    "type": "internal"},
    {"name": "بندرعباس",    "lat": 27.1832, "lon": 56.2666, "type": "internal"},
    {"name": "بوشهر",       "lat": 28.9234, "lon": 50.8200, "type": "internal"},
    {"name": "چابهار",      "lat": 25.2900, "lon": 60.6430, "type": "internal"},
    {"name": "بندر انزلی",   "lat": 37.4720, "lon": 49.4630, "type": "internal"},
    {"name": "تهران",       "lat": 35.6892, "lon": 51.3890, "type": "internal"},
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


def get_wind(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "wind_speed_10m,wind_direction_10m",
        "forecast_days": 2,
        "wind_speed_unit": "kmh",
        "timezone": "Asia/Tehran",
    }
    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("API error:", e)
        return None


def check_urgent():
    alerts = []
    now_tehran = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=3, minutes=30)

    for point in URGENT_POINTS:
        wind = get_wind(point["lat"], point["lon"])
        if not wind or "hourly" not in wind:
            continue
        hourly = wind["hourly"]
        times = hourly["time"]
        speeds = hourly["wind_speed_10m"]
        directions = hourly["wind_direction_10m"]

        for i, t in enumerate(times):
            try:
                alert_time = datetime.fromisoformat(t)
                diff = (alert_time - now_tehran).total_seconds() / 60
                if diff < 0 or diff > 120:
                    continue
            except Exception:
                continue

            speed = speeds[i]
            if speed is None or speed <= WIND_SPEED_THRESHOLD:
                continue

            alerts.append({
                "point": point["name"],
                "time": t,
                "speed": round(speed, 1),
                "direction": directions[i],
                "minutes_until": int(diff),
            })
            break

    return alerts


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
    print("هشدار فوری - " + now_jalali())
    print("=" * 60)

    alerts = check_urgent()
    print("Urgent alerts:", len(alerts))

    if not alerts:
        print("No urgent alerts. Nothing sent.")
        return

    msg = "🚨 **هشدار فوری طوفان** 🚨\n\n"
    msg += "📅 " + now_jalali() + "\n"
    msg += "━━━━━━━━━━━━━━━\n\n"
    for a in alerts:
        msg += "⚠️ **" + a["point"] + "**\n"
        msg += "   💨 سرعت باد: " + str(a["speed"]) + " km/h\n"
        msg += "   🕐 زمان: " + a["time"] + "\n"
        msg += "   ⏳ تا " + str(a["minutes_until"]) + " دقیقه دیگر\n\n"
    msg += "━━━━━━━━━━━━━━━\n"

    asyncio.run(send_to_all(msg))


if __name__ == "__main__":
    main()