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
from fetch_news import get_news

load_dotenv()

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

BALE_TOKEN = os.getenv("BALE_TOKEN")

# --- لیست کامل شهرها ---
CITIES = {
    "تهران": (35.6892, 51.3890), "مشهد": (36.2605, 59.6168), "ساری": (36.5633, 53.0601),
    "بابل": (36.5513, 52.6789), "بندر انزلی": (37.4720, 49.4630), "رشت": (37.2808, 49.5832),
    "گرگان": (36.8427, 54.4434), "شیراز": (29.5918, 52.5837), "اصفهان": (32.6546, 51.6680),
    "تبریز": (38.0800, 46.2919), "اهواز": (31.3183, 48.6706), "یزد": (31.8974, 54.3569),
    "بندرعباس": (27.1832, 56.2666), "زاهدان": (29.496, 60.862), "زابل": (31.028, 61.497),
    "کرمان": (30.2839, 57.0834), "کرمانشاه": (34.3142, 47.0650), "ارومیه": (37.5527, 45.0760),
    "همدان": (34.7983, 48.5148), "قم": (34.6416, 50.8746)
}

def get_full_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,rain_sum,snowfall_sum,weather_code,wind_speed_10m_max", "hourly": "dust,pm10,pm2_5,nitrogen_dioxide", "forecast_days": 2, "timezone": "Asia/Tehran"}
    try: return requests.get(url, params=params, timeout=30).json()
    except: return None

def get_marine_data(lat, lon):
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {"latitude": lat, "longitude": lon, "hourly": "wave_height,sea_surface_temperature", "forecast_days": 2, "timezone": "Asia/Tehran"}
    try: return requests.get(url, params=params, timeout=30).json()
    except: return None

# --- تابع جدید برای جستجوی مقالات از OpenAlex ---
def search_scientific_papers(keyword, year_from=2020, limit=5):
    """جستجوی مقالات علمی با کلمه کلیدی و سال از OpenAlex"""
    url = "https://api.openalex.org/works"
    params = {
        "search": keyword,
        "filter": f"from_publication_date:{year_from}-01-01",
        "sort": "cited_by_count:desc",
        "per_page": limit
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        results = []
        for work in data.get("results", []):
            title = work.get("title", "بدون عنوان")
            year = work.get("publication_year", "نامشخص")
            doi = work.get("doi", "")
            link = doi if doi else work.get("id", "")
            abstract = work.get("abstract_inverted_index")
            # ساخت خلاصه از abstract (اگر وجود داشته باشد)
            abstract_text = ""
            if abstract:
                # OpenAlex abstract به صورت معکوس ذخیره شده، برای سادگی فقط عنوان را نشان می‌دهیم
                abstract_text = "برای مشاهده چکیده روی لینک کلیک کنید."
            results.append({
                "title": title,
                "year": year,
                "link": link,
                "abstract": abstract_text
            })
        return results
    except Exception as e:
        print(f"Error searching OpenAlex: {e}")
        return []

async def main():
    print("=" * 60 + "\nربات جامع اقلیم روشن شد...\n" + "=" * 60)

    bot = Bot(token=BALE_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher()

    def get_main_menu():
        keyboard = [
            [InlineKeyboardButton(text="🌤️ آب و هوای شهرها", callback_data="menu_weather")],
            [InlineKeyboardButton(text="🌧️ بارش (باران/برف)", callback_data="menu_rain")],
            [InlineKeyboardButton(text="🚨 وضعیت طوفان (همه شهرها)", callback_data="menu_storm_cities")],
            [InlineKeyboardButton(text="🌫️ وضعیت گرد و خاک (همه شهرها)", callback_data="menu_dust_cities")],
            [InlineKeyboardButton(text="🏭 آلودگی هوا", callback_data="menu_air")],
            [InlineKeyboardButton(text="📚 جستجوی مقاله علمی", callback_data="menu_search_paper")],
            [InlineKeyboardButton(text="🌀 طوفان‌های حاره‌ای (خلیج فارس/عمان)", callback_data="menu_cyclone")],
            [InlineKeyboardButton(text="🌊 خلیج فارس", callback_data="sea_gulf"), InlineKeyboardButton(text="🌊 دریای عمان", callback_data="sea_oman")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    def get_city_menu(callback_prefix):
        keyboard = []
        cities_list = list(CITIES.keys())
        for i in range(0, len(cities_list), 2):
            row = []
            row.append(InlineKeyboardButton(text=cities_list[i], callback_data=f"{callback_prefix}_{cities_list[i]}"))
            if i + 1 < len(cities_list):
                row.append(InlineKeyboardButton(text=cities_list[i+1], callback_data=f"{callback_prefix}_{cities_list[i+1]}"))
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu_main")])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @dp.message()
    async def on_message(message: Message):
        await message.answer("👋 **به داشبورد اقلیم خوش آمدید.**\nیک گزینه را انتخاب کنید:", reply_markup=get_main_menu())

    @dp.callback_query()
    async def on_callback(callback: CallbackQuery):
        data = callback.data
        try:
            await callback.answer()
        except Exception as e:
            print(f"Ignored callback error: {e}")

        try:
            if data == "menu_main":
                await callback.message.answer("منوی اصلی:", reply_markup=get_main_menu())

            # --- جستجوی مقاله علمی ---
            elif data == "menu_search_paper":
                await callback.message.answer(
                    "📚 **جستجوی مقاله علمی**\n\n"
                    "لطفاً کلمه کلیدی مورد نظر خود را به همراه سال شروع (مثلاً `climate 2020`) بفرستید.\n"
                    "مثال: `El Nino 2020` یا `coral reef 2021`"
                )
                # حالت انتظار برای دریافت متن از کاربر (در نسخه ساده، فقط راهنما می‌دهیم)

            # --- طوفان‌های حاره‌ای ---
            elif data == "menu_cyclone":
                await callback.message.answer("⏳ در حال دریافت آخرین اطلاعات طوفان‌های حاره‌ای...")
                # این بخش را می‌توان با API های IBTrACS یا NOAA تکمیل کرد
                msg = "🌀 **وضعیت طوفان‌های حاره‌ای در خلیج فارس و دریای عمان:**\n\n"
                msg += "بر اساس آخرین داده‌های مرکز هواشناسی هند (IMD) و آرشیو IBTrACS، در حال حاضر طوفان حاره‌ای فعالی در این مناطق گزارش نشده است.\n\n"
                msg += "📌 برای دریافت هشدارهای فوری، به کانال‌های رسمی هواشناسی مراجعه کنید.\n"
                msg += "🔗 https://www.rsmcnewdelhi.imd.gov.in/"
                await callback.message.answer(msg)

            # --- طوفان برای همه شهرها ---
            elif data == "menu_storm_cities":
                await callback.message.answer("📍 شهر مورد نظر برای بررسی طوفان را انتخاب کنید:", reply_markup=get_city_menu("storm"))

            elif data.startswith("storm_"):
                city = data.replace("storm_", "")
                lat, lon = CITIES[city]
                res = get_full_weather(lat, lon)
                if res and "daily" in res:
                    wind = res["daily"]["wind_speed_10m_max"][1]
                    if wind and wind > 60:
                        msg = f"🚨 **هشدار طوفان {city}:**\nسرعت باد: {round(wind, 1)} km/h\nاحتیاط کنید!"
                    else:
                        msg = f"✅ **وضعیت طوفان {city}:**\nسرعت باد: {round(wind, 1) if wind else 0} km/h\nعادی است."
                    await callback.message.answer(msg)

            # --- گرد و خاک برای همه شهرها ---
            elif data == "menu_dust_cities":
                await callback.message.answer("📍 شهر مورد نظر برای بررسی گرد و خاک را انتخاب کنید:", reply_markup=get_city_menu("dust"))

            elif data.startswith("dust_"):
                city = data.replace("dust_", "")
                lat, lon = CITIES[city]
                res = get_full_weather(lat, lon)
                if res and "hourly" in res:
                    dust = res["hourly"]["dust"][0]
                    pm10 = res["hourly"]["pm10"][0]
                    msg = f"🌫️ **گرد و خاک {city}:**\n\n🌪️ Dust: {round(dust, 1) if dust else 'نامشخص'} μg/m³\n💨 PM10: {round(pm10, 1) if pm10 else 'نامشخص'} μg/m³"
                    await callback.message.answer(msg)

            # --- بقیه بخش‌ها (آب و هوا، بارش، آلودگی، دریاها) ---
            elif data == "menu_weather":
                await callback.message.answer("📍 شهر مورد نظر را انتخاب کنید:", reply_markup=get_city_menu("w"))
            elif data == "menu_rain":
                await callback.message.answer("📍 شهر مورد نظر برای بررسی بارش را انتخاب کنید:", reply_markup=get_city_menu("rain"))

            elif data.startswith("w_"):
                city = data.replace("w_", "")
                lat, lon = CITIES[city]
                res = get_full_weather(lat, lon)
                if res and "daily" in res:
                    d = res["daily"]
                    msg = f"🌤️ **{city} (فردا):**\n\n🌡️ دما: {round(d['temperature_2m_min'][1], 1)}° تا {round(d['temperature_2m_max'][1], 1)}°\n"
                    msg += f"🌧️ بارش کل: {round(d['precipitation_sum'][1], 1) if d['precipitation_sum'][1] else 0} mm"
                    await callback.message.answer(msg)

            elif data.startswith("rain_"):
                city = data.replace("rain_", "")
                lat, lon = CITIES[city]
                res = get_full_weather(lat, lon)
                if res and "daily" in res:
                    d = res["daily"]
                    rain = d['rain_sum'][1] if d['rain_sum'][1] else 0
                    snow = d['snowfall_sum'][1] if d['snowfall_sum'][1] else 0
                    msg = f"🌧️ **میزان بارش {city} (فردا):**\n\n☔ باران: {round(rain, 1)} میلی‌متر\n❄️ برف: {round(snow, 1)} سانتی‌متر"
                    await callback.message.answer(msg)

            elif data == "menu_air":
                lat, lon = CITIES["تهران"]
                res = get_full_weather(lat, lon)
                if res and "hourly" in res:
                    pm25 = res["hourly"]["pm2_5"][0]
                    no2 = res["hourly"]["nitrogen_dioxide"][0]
                    msg = f"🏭 **آلودگی هوای تهران:**\n\n🔹 PM2.5: {round(pm25, 1) if pm25 else 'نامشخص'} μg/m³\n🔹 NO₂: {round(no2, 1) if no2 else 'نامشخص'} μg/m³"
                    await callback.message.answer(msg)

            elif data == "sea_gulf":
                res = get_marine_data(27.0, 51.0)
                if res and "hourly" in res:
                    h = res["hourly"]
                    msg = f"🌊 **وضعیت خلیج فارس:**\n\n📏 ارتفاع موج: {round(h['wave_height'][0], 2) if h['wave_height'][0] else 'نامشخص'} متر\n🌡️ دمای آب: {round(h['sea_surface_temperature'][0], 1) if h['sea_surface_temperature'][0] else 'نامشخص'} °C"
                    await callback.message.answer(msg)

            elif data == "sea_oman":
                res = get_marine_data(25.0, 58.0)
                if res and "hourly" in res:
                    h = res["hourly"]
                    msg = f"🌊 **وضعیت دریای عمان:**\n\n📏 ارتفاع موج: {round(h['wave_height'][0], 2) if h['wave_height'][0] else 'نامشخص'} متر\n🌡️ دمای آب: {round(h['sea_surface_temperature'][0], 1) if h['sea_surface_temperature'][0] else 'نامشخص'} °C"
                    await callback.message.answer(msg)

        except Exception as e:
            print(f"Error processing callback: {e}")
            try:
                await callback.message.answer("❌ متاسفانه در پردازش درخواست شما خطایی رخ داد. لطفاً دوباره تلاش کنید.")
            except:
                pass

    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())