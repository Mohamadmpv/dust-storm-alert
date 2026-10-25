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
    
    # 1. زمان فعلی به وقت گرینویچ (UTC) را می‌گیریم
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    
    # 2. زمان فعلی به وقت تهران را برای چاپ در لاگ حساب می‌کنیم (فقط برای اینکه ببینید سیستم الان چه ساعتی است)
    now_tehran = now_utc + timedelta(hours=3, minutes=30)
    print(f"Current UTC: {now_utc} | Current Tehran: {now_tehran}")

    for point in URGENT_POINTS:
        wind = get_wind_data(point["lat"], point["lon"])
        if not wind or "hourly" not in wind:
            continue

        hourly = wind["hourly"]
        times = hourly["time"]
        speeds = hourly["wind_speed_10m"]
        directions = hourly["wind_direction_10m"]

        for i, time_str in enumerate(times):
            try:
                # API همیشه زمان را به UTC می‌دهد
                alert_time_utc = datetime.fromisoformat(time_str)
                
                # اختلاف زمانی: زمان هشدار (UTC) منهای زمان فعلی (UTC)
                diff_minutes = (alert_time_utc - now_utc).total_seconds() / 60
                
                # اگر زمان هشدار بین 0 تا 120 دقیقه آینده نبود، برو بعدی
                if diff_minutes < 0 or diff_minutes > 120:
                    continue
            except Exception:
                continue

            speed = speeds[i]
            if speed is None or speed <= WIND_SPEED_THRESHOLD:
                continue

            # برای نمایش در پیام، زمان UTC را به وقت تهران تبدیل می‌کنیم
            alert_time_tehran = alert_time_utc + timedelta(hours=3, minutes=30)
            
            alerts.append({
                "point": point["name"],
                "speed": round(speed, 1),
                "direction": directions[i],
                "analysis": analyze_wind_source(point["name"], directions[i]),
                "time_tehran": alert_time_tehran.strftime("%Y-%m-%d %H:%M") # ساعت دقیق تهران
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
            msg += f"⚠️ **{a['point']}**\n"
            msg += f"   💨 سرعت باد: {a['speed']} km/h\n"
            msg += f"   🧭 جهت باد: {a['direction']} درجه\n"
            msg += f"   📍 تحلیل: {a['analysis']}\n"
            msg += f"   🗓️ زمان دقیق: {a['time_tehran']} (به وقت تهران)\n"
            msg += "   📌 باد در ۲ ساعت آینده می‌رسد!\n\n"

        msg += "━━━━━━━━━━━━━━━\n"
        asyncio.run(_send_to_all(msg))
    else:
        print("No urgent alerts found. Weather is normal.")

if __name__ == "__main__":
    run_urgent()