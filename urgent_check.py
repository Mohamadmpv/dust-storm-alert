from api_client import get_wind_data
from config import WIND_SPEED_THRESHOLD
from notifier import _send_to_all
from jalali import now_jalali
from wind_analysis import analyze_wind_source
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import asyncio

URGENT_POINTS = [
    {"name": "دریای خزر",   "lat": 40.0,    "lon": 51.0,    "type": "internal"},
    {"name": "خلیج فارس",   "lat": 27.0,    "lon": 51.0,    "type": "internal"},
    {"name": "دریای عمان",  "lat": 25.0,    "lon": 58.0,    "type": "internal"},
    {"name": "بندرعباس",    "lat": 27.1832, "lon": 56.2666, "type": "internal"},
    {"name": "بوشهر",       "lat": 28.9234, "lon": 50.8200, "type": "internal"},
    {"name": "چابهار",      "lat": 25.2900, "lon": 60.6430, "type": "internal"},
    {"name": "بندر انزلی",   "lat": 37.4720, "lon": 49.4630, "type": "internal"},
    {"name": "تهران",       "lat": 35.6892, "lon": 51.3890, "type": "internal"},
    {"name": "زابل (سیستان)", "lat": 31.028, "lon": 61.497, "type": "internal"},
    {"name": "زاهدان",      "lat": 29.496, "lon": 60.862,  "type": "internal"},
    {"name": "اهواز",       "lat": 31.318,  "lon": 48.670,  "type": "internal"}
]

# حافظه موقت برای جلوگیری از ارسال تکراری (در طول یک اجرا)
sent_alerts_cache = {}

def check_urgent():
    global sent_alerts_cache
    alerts = []
    tehran_tz = ZoneInfo("Asia/Tehran")
    now_tehran = datetime.now(tehran_tz)

    # پاکسازی حافظه‌های قدیمی‌تر از 3 ساعت
    sent_alerts_cache = {k: v for k, v in sent_alerts_cache.items() if (now_tehran - v).total_seconds() < 10800}

    for point in URGENT_POINTS:
        wind = get_wind_data(point["lat"], point["lon"])
        if not wind or "hourly" not in wind: continue

        hourly = wind["hourly"]
        times = hourly["time"]
        speeds = hourly["wind_speed_10m"]
        directions = hourly["wind_direction_10m"]

        for i, time_str in enumerate(times):
            try:
                alert_time_utc = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)
                alert_time_tehran = alert_time_utc.astimezone(tehran_tz)
                diff_minutes = (alert_time_tehran - now_tehran).total_seconds() / 60
                
                if diff_minutes < -5 or diff_minutes > 120: continue
            except Exception: continue

            speed = speeds[i]
            if speed is None or speed <= WIND_SPEED_THRESHOLD: continue

            # بررسی اینکه آیا قبلاً این هشدار را فرستاده‌ایم یا نه
            alert_key = f"{point['name']}_{alert_time_tehran.strftime('%Y-%m-%d_%H')}"
            if alert_key in sent_alerts_cache:
                continue # اگر قبلاً فرستاده شده، نادیده بگیر

            alerts.append({
                "point": point["name"],
                "speed": round(speed, 1),
                "direction": directions[i],
                "analysis": analyze_wind_source(point["name"], directions[i]),
                "time_tehran": alert_time_tehran.strftime("%Y-%m-%d - %H:%M"),
                "cache_key": alert_key
            })
            break
    return alerts

def run_urgent():
    print("=" * 60 + "\nبررسی اضطراری - " + now_jalali() + "\n" + "=" * 60)
    alerts = check_urgent()
    
    if alerts:
        msg = "🚨 **هشدار فوری طوفان** 🚨\n\n📅 " + now_jalali() + "\n━━━━━━━━━━━━━━━\n\n"
        for a in alerts:
            date_part, time_part = a["time_tehran"].split(" - ")
            msg += f"⚠️ {a['point']}\n   💨 سرعت باد: {a['speed']} km/h\n   🧭 جهت باد: {a['direction']} درجه\n   📍 تحلیل: {a['analysis']}\n   🗓️ تاریخ: {date_part}\n   🕐 ساعت: {time_part}\n   📌 باد در ۲ ساعت آینده می‌رسد!\n\n"
            # ذخیره در حافظه
            sent_alerts_cache[a["cache_key"]] = datetime.now(ZoneInfo("Asia/Tehran"))
            
        msg += "━━━━━━━━━━━━━━━\n"
        asyncio.run(_send_to_all(msg))
    else:
        print("وضعیت عادی است.")

if __name__ == "__main__":
    run_urgent()