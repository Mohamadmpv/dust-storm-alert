from api_client import get_wind_data
from config import WIND_SPEED_THRESHOLD
from notifier import _send_to_all
from jalali import now_jalali, to_jalali
from wind_analysis import analyze_wind_source
from datetime import datetime, timezone, timedelta
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
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    now_tehran = now_utc + timedelta(hours=3, minutes=30)

    print(f"Checking urgent points... (Current Tehran Time: {now_tehran})")

    for point in URGENT_POINTS:
        print(f"Checking: {point['name']}")
        wind = get_wind_data(point["lat"], point["lon"])
        if not wind or "hourly" not in wind:
            print(f"  No data for {point['name']}")
            continue

        hourly = wind["hourly"]
        times = hourly["time"]
        speeds = hourly["wind_speed_10m"]
        directions = hourly["wind_direction_10m"]

        for i, time_str in enumerate(times):
            try:
                alert_time = datetime.fromisoformat(time_str)
                alert_time_tehran = alert_time + timedelta(hours=3, minutes=30)
                diff_minutes = (alert_time_tehran - now_tehran).total_seconds() / 60
                if diff_minutes < 0 or diff_minutes > 120:
                    continue
            except Exception:
                continue

            speed = speeds[i]
            if speed is None or speed <= WIND_SPEED_THRESHOLD:
                continue

            print(f"  ALERT FOUND: {point['name']} - Speed: {speed} km/h")
            alerts.append({
                "point": point["name"],
                "speed": round(speed, 1),
                "direction": directions[i],
                "analysis": analyze_wind_source(point["name"], directions[i]),
                "time": time_str
            })
            break

    return alerts

def run_urgent():
    print("=" * 60)
    print("بررسی اضطراری - " + now_jalali())
    print("=" * 60)

    alerts = check_urgent()

    if alerts:
        print(f"Total urgent alerts found: {len(alerts)}")
        msg = "🚨 **هشدار فوری طوفان** 🚨\n\n"
        msg += "📅 " + now_jalali() + "\n"
        msg += "━━━━━━━━━━━━━━━\n\n"

        for a in alerts:
            msg += f"⚠️ **{a['point']}**\n"
            msg += f"   💨 سرعت باد: {a['speed']} km/h\n"
            msg += f"   🧭 جهت باد: {a['direction']} درجه\n"
            msg += f"   📍 تحلیل: {a['analysis']}\n"
            
            jalali_time = to_jalali(a["time"])
            if " - " in jalali_time:
                date_part, time_part = jalali_time.split(" - ")
                msg += f"   🗓️ تاریخ: {date_part}\n"
                msg += f"   🕐 ساعت: {time_part}\n"
            else:
                msg += f"   🕐 زمان: {jalali_time}\n"
                
            msg += "   📌 باد در ۲ ساعت آینده می‌رسد!\n\n"

        msg += "━━━━━━━━━━━━━━━\n"
        print("Sending urgent alert...")
        asyncio.run(_send_to_all(msg))
        print("Urgent alert sent successfully.")
    else:
        print("No urgent alerts found. Weather is normal.")

if __name__ == "__main__":
    run_urgent()