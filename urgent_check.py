"""
بررسی اضطراری: فقط نقاط حساس (دریاها و بنادر) را چک می‌کند.
اگر باد بالا باشد، هشدار فوری می‌فرستد.
"""
from api_client import get_wind_data
from config import WIND_SPEED_THRESHOLD
from notifier import send_alert
from jalali import now_jalali
from datetime import datetime, timezone, timedelta

# نقاط حساس (دریاها + بنادر + تهران)
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


def check_urgent():
    """بررسی سریع نقاط حساس"""
    alerts = []
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    now_tehran = now_utc + timedelta(hours=3, minutes=30)

    for point in URGENT_POINTS:
        wind = get_wind_data(point["lat"], point["lon"])
        if not wind or "hourly" not in wind:
            continue

        hourly = wind["hourly"]
        times = hourly["time"]
        speeds = hourly["wind_speed_10m"]
        directions = hourly["wind_direction_10m"]

        for i, time_str in enumerate(times):
            # فقط ۲ ساعت آینده را چک کن
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

            # اگر باد بالای آستانه و در ۲ ساعت آینده بود
            alert = {
                "point": point["name"],
                "type": point["type"],
                "message": "هشدار فوری: باد به‌زودی می‌رسد",
                "time": time_str,
                "speed": round(speed, 1),
                "direction": directions[i],
                "gust": None,
                "severity": "WARNING",
                "forecast": None,
            }
            alerts.append(alert)
            break  # فقط اولین هشدار هر نقطه

    return alerts


if __name__ == "__main__":
    print("=" * 60)
    print("بررسی اضطراری - " + now_jalali())
    print("=" * 60)

    alerts = check_urgent()

    if alerts:
        print("هشدار فوری یافت شد:", len(alerts))
        send_alert(alerts)
    else:
        print("وضعیت عادی است.")