import asyncio
import requests
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from jalali import now_jalali, to_jalali
from notifier import _send_to_all_async
from config import BALE_TOKEN, TELEGRAM_TOKEN, GIST_ID, GH_PAT
import os
import json

# آستانه بارش برای هشدار سیل (میلی‌متر در 2 ساعت)
FLOOD_THRESHOLD_2H = 10.0

# شهرهای مهم برای پایش سیل
FLOOD_CITIES = [
    {"name": "تهران", "lat": 35.6892, "lon": 51.3890},
    {"name": "تبریز", "lat": 38.0800, "lon": 46.2919},
    {"name": "اهواز", "lat": 31.3183, "lon": 48.6706},
    {"name": "اصفهان", "lat": 32.6546, "lon": 51.6680},
    {"name": "بندرعباس", "lat": 27.1832, "lon": 56.2666},
    {"name": "بوشهر", "lat": 28.9234, "lon": 50.8200},
    {"name": "چابهار", "lat": 25.2900, "lon": 60.6430},
    {"name": "بندر انزلی", "lat": 37.4720, "lon": 49.4630},
    {"name": "زابل (سیستان)", "lat": 31.028, "lon": 61.497},
    {"name": "زاهدان", "lat": 29.496, "lon": 60.862},
    {"name": "شیراز", "lat": 29.5918, "lon": 52.5837},
    {"name": "مشهد", "lat": 36.2605, "lon": 59.6168},
]

def get_precipitation_data(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "precipitation",
        "forecast_days": 1,
        "timezone": "Asia/Tehran"
    }
    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error fetching precipitation: {e}")
        return None

async def main():
    print("=" * 60)
    print("بررسی فوری سیل - " + now_jalali())
    print("=" * 60)

    tehran_tz = ZoneInfo("Asia/Tehran")
    now_tehran = datetime.now(tehran_tz)
    
    alerts = []

    for city in FLOOD_CITIES:
        data = get_precipitation_data(city["lat"], city["lon"])
        if not data or "hourly" not in data:
            continue
        
        hourly = data["hourly"]
        times = hourly["time"]
        precip = hourly["precipitation"]
        
        # بررسی 2 ساعت آینده
        total_rain_2h = 0
        has_alert = False
        
        for i, time_str in enumerate(times):
            try:
                alert_time = datetime.fromisoformat(time_str).replace(tzinfo=tehran_tz)
                diff_minutes = (alert_time - now_tehran).total_seconds() / 60
                
                # اگر زمان بین 0 تا 120 دقیقه آینده بود
                if 0 <= diff_minutes <= 120:
                    if precip[i] is not None and precip[i] > 0:
                        total_rain_2h += precip[i]
                        if total_rain_2h >= FLOOD_THRESHOLD_2H:
                            has_alert = True
                            break
            except Exception:
                continue
        
        if has_alert:
            alerts.append({
                "name": city["name"],
                "rain": round(total_rain_2h, 1)
            })

    if alerts:
        msg = "🚨 **هشدار فوری سیل** 🚨\n\n"
        msg += "📅 " + now_jalali() + "\n"
        msg += "━━━━━━━━━━━━━━━\n\n"
        msg += "بارش شدید برای **۲ ساعت آینده** پیش‌بینی شده است:\n\n"
        
        for a in alerts:
            msg += f"⚠️ **{a['name']}**: {a['rain']} میلی‌متر بارش\n"
        
        msg += "\n📌 **توصیه:** از تردد در حاشیه رودخانه‌ها، مسیل‌ها و مناطق پست خودداری کنید.\n"
        msg += "━━━━━━━━━━━━━━━\n"
        
        # استفاده از یک شناسه یکتا بر اساس زمان (برای جلوگیری از تکرار در 2 ساعت)
        alert_id = f"flood_{now_tehran.strftime('%Y-%m-%d_%H')}"
        await _send_to_all_async(msg, message_id=alert_id)
        print("Flood alert sent!")
    else:
        print("No flood risk detected in the next 2 hours.")

if __name__ == "__main__":
    asyncio.run(main())