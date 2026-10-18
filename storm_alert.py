import asyncio
import json
import requests
from telegram import Bot as TelegramBot
from datetime import datetime, timezone, timedelta
import os
from config import BALE_TOKEN, TELEGRAM_TOKEN, GIST_ID, GH_PAT, WIND_SPEED_THRESHOLD
from jalali import now_jalali

URGENT_POINTS = [
    {"name": "دریای خزر",   "lat": 40.0,    "lon": 51.0},
    {"name": "خلیج فارس",   "lat": 27.0,    "lon": 51.0},
    {"name": "دریای عمان",  "lat": 25.0,    "lon": 58.0},
    {"name": "بندرعباس",    "lat": 27.1832, "lon": 56.2666},
    {"name": "بوشهر",       "lat": 28.9234, "lon": 50.8200},
    {"name": "چابهار",      "lat": 25.2900, "lon": 60.6430},
    {"name": "بندر انزلی",   "lat": 37.4720, "lon": 49.4630},
    {"name": "تهران",       "lat": 35.6892, "lon": 51.3890},
]

def get_gist_users(filename):
    url = "https://api.github.com/gists/" + GIST_ID
    headers = {"Authorization": "token " + GH_PAT}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        content = r.json()["files"].get(filename, {}).get("content", "")
        return json.loads(content) if content else {}
    except Exception:
        return {}

def get_wind(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "hourly": "wind_speed_10m", "forecast_days": 2, "wind_speed_unit": "kmh", "timezone": "Asia/Tehran"}
    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def check_urgent():
    alerts = []
    now_tehran = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=3, minutes=30)
    
    for p in URGENT_POINTS:
        wind = get_wind(p["lat"], p["lon"])
        if not wind or "hourly" not in wind: continue
        times, speeds = wind["hourly"]["time"], wind["hourly"]["wind_speed_10m"]
        
        for i, t in enumerate(times):
            try:
                alert_time_tehran = datetime.fromisoformat(t)
                diff = (alert_time_tehran - now_tehran).total_seconds() / 60
                if diff < 0 or diff > 120: continue
            except Exception: continue
            
            if speeds[i] and speeds[i] > WIND_SPEED_THRESHOLD:
                alerts.append({
                    "point": p["name"],
                    "time_tehran": alert_time_tehran.strftime("%Y-%m-%d %H:%M"),
                    "speed": round(speeds[i], 1),
                    "minutes": int(diff)
                })
                break
    return alerts

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
    if not BALE_TOKEN:
        print("  Bale Failed: Token is None")
        return
    for cid in users.keys():
        url = f"https://tapi.bale.ai/bot{BALE_TOKEN}/sendMessage"
        try:
            r = requests.post(url, json={"chat_id": cid, "text": msg, "parse_mode": "Markdown"}, timeout=30)
            r.raise_for_status()
            print("  Bale Sent:", cid)
        except Exception as e:
            print("  Bale Failed:", cid, e)

async def main():
    print("=" * 60 + "\nهشدار فوری - " + now_jalali() + "\n" + "=" * 60)
    alerts = check_urgent()
    print("Urgent alerts:", len(alerts))
    
    if not alerts:
        print("No urgent alerts. Nothing sent.")
        return
        
    # ✅ اینجا قسمت گرافیکی و مرتب پیام هشدار است
    msg = "🚨 **هشدار فوری طوفان** 🚨\n"
    msg += "📅 " + now_jalali() + "\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for a in alerts:
        msg += f"⚠️ **{a['point']}**\n"
        msg += f"   💨 سرعت باد: {a['speed']} km/h\n"
        msg += f"   🕐 زمان: {a['time_tehran']}\n"
        msg += f"   ⏳ حدود {a['minutes']} دقیقه دیگر\n"
        msg += "   ➖➖➖➖➖➖\n"
        
    msg += "\n━━━━━━━━━━━━━━━━━━━━\n"
    
    await send_telegram(msg)
    send_bale(msg)

if __name__ == "__main__":
    asyncio.run(main())