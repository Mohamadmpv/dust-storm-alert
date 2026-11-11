import asyncio
import logging
import sys
import os
import requests
from datetime import datetime, timedelta
from baleio import Bot, Dispatcher, md, types
from baleio.client.default import DefaultBotProperties
from baleio.enums import ParseMode
from baleio.types import Message, CallbackQuery
from baleio.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from marine_predict import predict_marine

load_dotenv()

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

BALE_TOKEN = os.getenv("BALE_TOKEN")

# مختصات خلیج فارس برای بخش دریا
LAT_GULF = 27.1832
LON_GULF = 56.2666

def get_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code", "forecast_days": 2, "timezone": "Asia/Tehran"}
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def get_dust(lat, lon):
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {"latitude": lat, "longitude": lon, "hourly": "dust,pm10", "forecast_days": 2, "timezone": "Asia/Tehran"}
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def get_air_quality(lat, lon):
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {"latitude": lat, "longitude": lon, "hourly": "pm2_5,pm10,nitrogen_dioxide", "forecast_days": 1, "timezone": "Asia/Tehran"}
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def get_marine_data(lat, lon):
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {"latitude": lat, "longitude": lon, "hourly": "wave_height,sea_surface_temperature", "forecast_days": 2, "timezone": "Asia/Tehran"}
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

async def main():
    print("=" * 60)
    print("ربات بله (داشبورد جامع) در حال اجراست...")
    print("=" * 60)

    bot = Bot(token=BALE_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    me = await bot.get_me()
    print(f"Bot @{me.username} is listening...")

    dp = Dispatcher()

    # --- تابع ساخت منوی اصلی ---
    def get_main_menu():
        keyboard = [
            [InlineKeyboardButton(text="🌤️ آب و هوا", callback_data="menu_weather")],
            [InlineKeyboardButton(text="🌊 وضعیت امواج دریا", callback_data="menu_waves")],
            [InlineKeyboardButton(text="🚨 وضعیت سیل", callback_data="menu_flood")],
            [InlineKeyboardButton(text="🌡️ دما", callback_data="menu_temp")],
            [InlineKeyboardButton(text="🌫️ وضعیت گرد و غبار", callback_data="menu_dust")],
            [InlineKeyboardButton(text="🏭 وضعیت آلودگی هوا", callback_data="menu_air")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @dp.message()
    async def on_message(message: Message):
        # نمایش منوی اصلی به کاربر
        await message.answer("👋 **به ربات پایش اقلیم خوش آمدید.**\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=get_main_menu())

    @dp.callback_query()
    async def on_callback(callback: CallbackQuery):
        data = callback.data
        await callback.answer() # بستن لودینگ دکمه

        # ۱. آب و هوا (نیاز به انتخاب شهر دارد)
        if data == "menu_weather":
            keyboard = [
                [InlineKeyboardButton(text="تهران", callback_data="weather_تهران"), InlineKeyboardButton(text="مشهد", callback_data="weather_مشهد")],
                [InlineKeyboardButton(text="بندر انزلی", callback_data="weather_بندر انزلی"), InlineKeyboardButton(text="رشت", callback_data="weather_رشت")],
                [InlineKeyboardButton(text="ساری", callback_data="weather_ساری"), InlineKeyboardButton(text="تبریز", callback_data="weather_تبریز")],
                [InlineKeyboardButton(text="بازگشت", callback_data="menu_main")]
            ]
            await callback.message.answer("📍 لطفاً شهر مورد نظر خود را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

        # ۲. وضعیت امواج دریا (خلیج فارس)
        elif data == "menu_waves":
            await callback.message.answer("⏳ در حال دریافت وضعیت امواج خلیج فارس...")
            marine = get_marine_data(LAT_GULF, LON_GULF)
            if marine and "hourly" in marine:
                h = marine["hourly"]
                wave = h["wave_height"][0]
                sst = h["sea_surface_temperature"][0]
                msg = f"🌊 **وضعیت امواج خلیج فارس:**\n\n"
                msg += f"📏 ارتفاع موج: {round(wave, 2) if wave else 'نامشخص'} متر\n"
                msg += f"🌡️ دمای سطح آب: {round(sst, 1) if sst else 'نامشخص'} °C\n"
                await callback.message.answer(msg)
            else:
                await callback.message.answer("❌ خطا در دریافت داده‌های دریایی.")

        # ۳. وضعیت سیل (تهران)
        elif data == "menu_flood":
            await callback.message.answer("⏳ در حال بررسی احتمال سیل...")
            weather = get_weather(35.6892, 51.3890)
            if weather and "daily" in weather:
                rain = weather["daily"]["precipitation_sum"][1]
                if rain and rain > 10:
                    msg = f"🚨 **هشدار سیل برای تهران:**\nبارش پیش‌بینی شده: {round(rain, 1)} میلی‌متر\nلطفاً احتیاط کنید."
                else:
                    msg = f"✅ **وضعیت سیل تهران:**\nبارش پیش‌بینی شده: {round(rain, 1) if rain else 0} میلی‌متر\nوضعیت عادی است."
                await callback.message.answer(msg)

        # ۴. دما (تهران)
        elif data == "menu_temp":
            await callback.message.answer("⏳ در حال دریافت دما...")
            weather = get_weather(35.6892, 51.3890)
            if weather and "daily" in weather:
                tmax = weather["daily"]["temperature_2m_max"][1]
                tmin = weather["daily"]["temperature_2m_min"][1]
                msg = f"🌡️ **دمای تهران (فردا):**\n\nحداکثر: {round(tmax, 1)}°C\nحداقل: {round(tmin, 1)}°C"
                await callback.message.answer(msg)

        # ۵. وضعیت گرد و غبار (تهران)
        elif data == "menu_dust":
            await callback.message.answer("⏳ در حال دریافت وضعیت گرد و غبار...")
            dust = get_dust(35.6892, 51.3890)
            if dust and "hourly" in dust:
                h = dust["hourly"]
                dust_val = h["dust"][0]
                pm10 = h["pm10"][0]
                msg = f"🌫️ **وضعیت گرد و غبار تهران:**\n\n"
                msg += f"🌪️ گرد و غبار: {round(dust_val, 1) if dust_val else 'نامشخص'} μg/m³\n"
                msg += f"💨 PM10: {round(pm10, 1) if pm10 else 'نامشخص'} μg/m³\n"
                await callback.message.answer(msg)

        # ۶. وضعیت آلودگی هوا (تهران)
        elif data == "menu_air":
            await callback.message.answer("⏳ در حال دریافت وضعیت آلودگی هوا...")
            air = get_air_quality(35.6892, 51.3890)
            if air and "hourly" in air:
                h = air["hourly"]
                pm25 = h["pm2_5"][0]
                pm10 = h["pm10"][0]
                no2 = h["nitrogen_dioxide"][0]
                msg = f"🏭 **آلودگی هوای تهران:**\n\n"
                msg += f"🔹 PM2.5: {round(pm25, 1) if pm25 else 'نامشخص'} μg/m³\n"
                msg += f"🔹 PM10: {round(pm10, 1) if pm10 else 'نامشخص'} μg/m³\n"
                msg += f"🔹 NO₂: {round(no2, 1) if no2 else 'نامشخص'} μg/m³\n"
                await callback.message.answer(msg)

        # انتخاب شهر برای آب و هوا
        elif data.startswith("weather_"):
            city = data.replace("weather_", "")
            lat, lon = 35.6892, 51.3890 # پیش‌فرض تهران
            # می‌توانید مختصات دقیق شهرها را اینجا تعریف کنید
            await callback.message.answer(f"⏳ در حال دریافت آب‌وهوای {city}...")
            weather = get_weather(lat, lon) # فعلاً برای سادگی از مختصات تهران استفاده می‌کنیم
            if weather and "daily" in weather:
                msg = f"🌤️ **آب‌وهوای {city} (فردا):**\n\nدما: {round(weather['daily']['temperature_2m_min'][1], 1)}° تا {round(weather['daily']['temperature_2m_max'][1], 1)}°\nبارش: {round(weather['daily']['precipitation_sum'][1], 1) if weather['daily']['precipitation_sum'][1] else 0} میلی‌متر"
                await callback.message.answer(msg)

        # بازگشت به منوی اصلی
        elif data == "menu_main":
            await callback.message.answer("منوی اصلی:", reply_markup=get_main_menu())

    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())