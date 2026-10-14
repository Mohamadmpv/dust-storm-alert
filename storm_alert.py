"""
هشدار فوری طوفان - برای تلگرام و بله
"""
import asyncio
import os
import json
import requests
from telegram import Bot as TelegramBot
from baleio import Bot as BaleBot
from baleio.client.default import DefaultBotProperties
from baleio.enums import ParseMode
from datetime import datetime, timezone, timedelta
from jalali import now_jalali


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BALE_TOKEN = os.getenv("BALE_TOKEN")
GIST_ID = os.getenv("GIST_ID")
GH_PAT = os.getenv("GH_PAT")

WIND_SPEED_THRESHOLD = 20

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


def get_gist_file(filename):
    url = "https://api.github.com/gists/" + GIST_ID
    headers = {"Authorization": "token " + GH_PAT}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()["files"].get(filename, {}).get("content", "")
    except Exception as e:
        print("Gist read error:", e)
        return ""


def get_telegram_users():
    content = get_gist_file("telegram_users.json")
    try:
        return json.loads(content) if content else {}
    except Exception:
        return {}


def get_bale_users():
    content = get_gist_file("bale_users.json")
    try:
        return json.loads(content) if content else {}
    except Exception:
        return {}


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


async def send_telegram(message):
    users = get_telegram_users()
    if not users:
        print("No Telegram users.")
        return
    bot = TelegramBot(token=TELEGRAM_TOKEN)
    print("Telegram recipients:", len(users))
    for cid in users.keys():
        try:
            await bot.send_message(chat_id=cid, text=message)
            print("  TG Sent:", cid)
        except Exception as e:
            print("  TG Failed:", cid, e)


async def send_bale(message):
    users = get_bale_users()
    if not users:
        print("No Bale users.")
        return
    bot = BaleBot(
        token=BALE_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    print("Bale recipients:", len(users))
    for cid in users.keys():
        try:
            await bot.send_message(chat_id=cid, text=message)
            print("  Bale Sent:", cid)
        except Exception as e:
            print("  Bale Failed:", cid, e)
    await bot.session.close()


async def main():
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

    await send_telegram(msg)
    await send_bale(msg)


if __name__ == "__main__":
    asyncio.run(main())