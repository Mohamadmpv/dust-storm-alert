from api_client import get_wind_data, get_dust_data
from config import (
    SOURCE_POINTS,
    WIND_SPEED_THRESHOLD,
    MIN_DIRECTION,
    MAX_DIRECTION,
)


def is_toward_iran(direction):
    if direction is None:
        return False
    return MIN_DIRECTION <= direction <= MAX_DIRECTION


def calculate_severity(speed):
    if speed > 90:
        return "CRITICAL"
    elif speed > 70:
        return "SEVERE"
    elif speed > 60:
        return "MODERATE"
    else:
        return "WARNING"


def analyze_point(point):
    alerts = []
    wind = get_wind_data(point["lat"], point["lon"])
    if not wind or "hourly" not in wind:
        return alerts

    hourly = wind["hourly"]
    times = hourly["time"]
    speeds = hourly["wind_speed_10m"]
    directions = hourly["wind_direction_10m"]
    gusts = hourly.get("wind_gusts_10m", [None] * len(times))

    # ✅ زمان فعلی (UTC)
    from datetime import datetime, timezone
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    for i, time_str in enumerate(times):
        # ✅ فیلتر: فقط زمان‌های آینده
        try:
            # Open-Meteo زمان را به فرمت ISO می‌دهد: "2026-10-10T06:00"
            alert_time = datetime.fromisoformat(time_str)
            if alert_time < now_utc:
                continue  # این زمان گذشته، رد کن
        except Exception:
            pass

        speed = speeds[i]
        direction = directions[i]

        if speed is None or speed <= WIND_SPEED_THRESHOLD:
            continue

        if point["type"] == "external":
            if not is_toward_iran(direction):
                continue
            alert_msg = "منشأ گرد و خاک خارجی، احتمال حرکت به سمت ایران"
        else:
            alert_msg = "باد شدید / احتمال گرد و خاک در این شهر"

        # پیش‌بینی ساعت بعد
        forecast_info = None
        if i + 1 < len(speeds):
            next_speed = speeds[i + 1]
            next_dir = directions[i + 1]
            if next_speed is not None and next_speed > WIND_SPEED_THRESHOLD:
                forecast_info = {
                    "next_time": times[i + 1],
                    "next_speed": round(next_speed, 1),
                    "next_direction": next_dir,
                }

        alert = {
            "point": point["name"],
            "type": point["type"],
            "message": alert_msg,
            "time": time_str,
            "speed": round(speed, 1),
            "direction": direction,
            "gust": round(gusts[i], 1) if gusts[i] else None,
            "severity": calculate_severity(speed),
            "forecast": forecast_info,
        }
        alerts.append(alert)

    return alerts


def detect_forecast_alert(point, hours_ahead=6):
    """
    هشدار پیش‌بینانه: اگر در چند ساعت آینده باد از آستانه عبور کند،
    حتی اگر الان آرام باشد.
    """
    wind = get_wind_data(point["lat"], point["lon"])
    if not wind or "hourly" not in wind:
        return None

    hourly = wind["hourly"]
    times = hourly["time"]
    speeds = hourly["wind_speed_10m"]
    directions = hourly["wind_direction_10m"]

    # پیدا کردن اولین زمانی که باد از آستانه عبور می‌کند
    for i in range(min(hours_ahead, len(speeds))):
        speed = speeds[i]
        direction = directions[i]
        if speed is None or speed <= WIND_SPEED_THRESHOLD:
            continue

        # برای نقاط خارجی، جهت هم مهم است
        if point["type"] == "external" and not is_toward_iran(direction):
            continue

        return {
            "point": point["name"],
            "type": point["type"],
            "time": times[i],
            "speed": round(speed, 1),
            "direction": direction,
            "hours_until": i,
        }

    return None


def detect_all():
    """جمع‌آوری هشدارهای فعلی + پیش‌بینانه"""
    all_alerts = []
    forecast_alerts = []

    for point in SOURCE_POINTS:
        print("Checking:", point["name"])

        # هشدارهای فعلی
        alerts = analyze_point(point)
        if alerts:
            print("  Found", len(alerts), "alerts")
        all_alerts.extend(alerts)

        # هشدار پیش‌بینانه (اگر الان آرام بود، ولی در آینده شدید می‌شود)
        if not alerts:
            fc = detect_forecast_alert(point, hours_ahead=6)
            if fc:
                forecast_alerts.append(fc)
                print("  Forecast alert:", fc["time"], "-", fc["speed"], "km/h")

    return all_alerts, forecast_alerts


if __name__ == "__main__":
    current, forecasts = detect_all()
    print()
    print("=" * 60)
    print("Current alerts:", len(current))
    print("Forecast alerts:", len(forecasts))
    print("=" * 60)