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

def check_urgent():
    alerts = []
    # 1. زمان فعلی دقیق به وقت تهران
    tehran_tz = ZoneInfo("Asia/Tehran")
    now_tehran = datetime.now(tehran_tz)

    for point in URGENT_POINTS:
        wind = get_wind_data(point["lat"], point["lon"])
        if not wind or "hourly" not in wind: continue

        hourly = wind["hourly"]
        times = hourly["time"]
        speeds = hourly["wind_speed_10m"]
        directions = hourly["wind_direction_10m"]

        for i, time_str in enumerate(times):
            try:
                # 2. تبدیل زمان UTC (دریافتی از API) به وقت تهران
                alert_time_utc = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)
                alert_time_tehran = alert_time_utc.astimezone(tehran_tz)
                
                # 3. محاسبه اختلاف دقیق به دقیقه
                diff_minutes = (alert_time_tehran - now_tehran).total_seconds() / 60
                
                # 4. فیلتر سخت‌گیرانه: فقط بین 0 تا 120 دقیقه آینده
                if diff_minutes < 0 or diff_minutes > 120:
                    continue
            except Exception:
                continue

            speed = speeds[i]
            if speed is None or speed <= WIND_SPEED_THRESHOLD:
                continue

            alerts.append({
                "point": point["name"],
                "speed": round(speed, 1),
                "direction": directions[i],
                "analysis": analyze_wind_source(point["name"], directions[i]),
                "time_tehran": alert_time_tehran.strftime("%Y-%m-%d - %H:%M")
            })
            break

    return alerts

def run_urgent():
    print("=" * 60)
    print("بررسی اضطراری - " + now_jalali())
    print("=" * 60)

    alerts = check_urgent()

    if alerts:
        msg = "🚨 **هشدار فوری طوفان** 🚨\n\n"
        msg += "📅 " + now_jalali() + "\n"
        msg += "━━━━━━━━━━━━━━━\n\n"

        for a in alerts:
            date_part, time_part = a["time_tehran"].split(" - ")
            msg += f"⚠️ **{a['point']}**\n"
            msg += f"   💨 سرعت باد: {a['speed']} km/h\n"
            msg += f"   🧭 جهت باد: {a['direction']} درجه\n"
            msg += f"   📍 تحلیل: {a['analysis']}\n"
            msg += f"   🗓️ تاریخ: {date_part}\n"
            msg += f"   🕐 ساعت: {time_part}\n"
            msg += "   📌 باد در ۲ ساعت آینده می‌رسد!\n\n"

        msg += "━━━━━━━━━━━━━━━\n"
        asyncio.run(_send_to_all(msg))
    else:
        print("وضعیت عادی است.")

if __name__ == "__main__":
    run_urgent()