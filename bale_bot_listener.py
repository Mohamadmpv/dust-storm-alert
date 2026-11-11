import asyncio
import logging
import sys
import os
import requests
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

CITIES = {
    "تهران": (35.6892, 51.3890), "مشهد": (36.2605, 59.6168), "ساری": (36.5633, 53.0601),
    "بابل": (36.5513, 52.6789), "بندر انزلی": (37.4720, 49.4630), "رشت": (37.2808, 49.5832),
    "گرگان": (36.8427, 54.4434), "شیراز": (29.5918, 52.5837), "اصفهان": (32.6546, 51.6680),
    "تبریز": (38.0800, 46.2919), "اهواز": (31.3183, 48.6706), "یزد": (31.8974, 54.3569),
    "بندرعباس": (27.1832, 56.2666), "زاهدان": (29.496, 60.862), "زابل": (31.028, 61.497),
    "کرمان": (30.2839, 57.0834), "کرمانشاه": (34.3142, 47.0650), "ارومیه": (37.5527, 45.0760),
    "همدان": (34.7983, 48.5148), "قم": (34.6416, 50.8746)
}

KEYWORD_TOPICS = [
    ("تغییرات اقلیمی", "climate change"), ("ال نینو", "El Nino"),
    ("گرمایش جهانی", "global warming"), ("مرجان‌های خلیج فارس", "Persian Gulf coral"),
    ("گرد و غبار", "dust storm"), ("آلودگی هوا", "air pollution"),
    ("طوفان حاره‌ای", "tropical cyclone"), ("بالا آمدن سطح آب دریا", "sea level rise"),
    ("خشکسالی", "drought"), ("انرژی‌های تجدیدپذیر", "renewable energy")
]

def get_full_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,rain_sum,snowfall_sum,weather_code,wind_speed_10m_max", "hourly": "dust,pm10", "forecast_days": 2, "timezone": "Asia/Tehran"}
    try: return requests.get(url, params=params, timeout=30).json()
    except: return None

# --- تابع جدید برای دریافت آلودگی هوا از API اختصاصی ---
def get_air_quality(lat, lon):
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "pm2_5,nitrogen_dioxide",
        "forecast_days": 1,
        "timezone": "Asia/Tehran"
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error fetching air quality: {e}")
        return None

def get_marine_data(lat, lon):
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {"latitude": lat, "longitude": lon, "hourly": "wave_height,sea_surface_temperature", "forecast_days": 2, "timezone": "Asia/Tehran"}
    try: return requests.get(url, params=params, timeout=30).json()
    except: return None

def search_openalex(keyword, year_from=2020, page=1):
    url = "https://api.openalex.org/works"
    params = {
        "search": keyword, "filter": f"from_publication_date:{year_from}-01-01",
        "sort": "relevance_score:desc", "per_page": 5, "page": page
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
            authors = work.get("authorships", [])
            author_name = authors[0].get("author", {}).get("display_name", "نامشخص") if authors else "نامشخص"
            results.append({"title": title, "year": year, "link": link, "author": author_name})
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
            [InlineKeyboardButton(text="🏭 آلودگی هوا (همه شهرها)", callback_data="menu_air_cities")],
            [InlineKeyboardButton(text="📚 جستجوی مقاله علمی", callback_data="menu_search_paper")],
            [InlineKeyboardButton(text="🌀 طوفان‌های حاره‌ای", callback_data="menu_cyclone")],
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

    def get_keyword_menu():
        keyboard = []
        for i in range(0, len(KEYWORD_TOPICS), 2):
            row = []
            row.append(InlineKeyboardButton(text=KEYWORD_TOPICS[i][0], callback_data=f"kw_{KEYWORD_TOPICS[i][1]}"))
            if i + 1 < len(KEYWORD_TOPICS):
                row.append(InlineKeyboardButton(text=KEYWORD_TOPICS[i+1][0], callback_data=f"kw_{KEYWORD_TOPICS[i+1][1]}"))
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

            elif data == "menu_search_paper":
                await callback.message.answer("📚 **جستجوی مقاله علمی**\n\nلطفاً یکی از موضوعات زیر را انتخاب کنید (مقالات از سال ۲۰۲۰ به بعد):", reply_markup=get_keyword_menu())

            elif data.startswith("kw_") and not data.startswith("kwmore_"):
                keyword_en = data.replace("kw_", "")
                await callback.message.answer(f"⏳ در حال جستجوی مقالات برای «{keyword_en}» از سال ۲۰۲۰...")
                results = search_openalex(keyword_en, 2020, page=1)
                if results:
                    msg = f"📚 **نتایج جستجو برای «{keyword_en}» (صفحه ۱):**\n\n━━━━━━━━━━━━━━━\n\n"
                    for i, res in enumerate(results, 1):
                        msg += f"{i}. **{res['title']}**\n   👤 {res['author']} | 📅 {res['year']}\n   🔗 [مشاهده مقاله]({res['link']})\n\n"
                    msg += "━━━━━━━━━━━━━━━\n"
                    keyboard = [[InlineKeyboardButton(text="📄 مقالات بیشتر (صفحه بعد)", callback_data=f"kwmore_{keyword_en}_2")]]
                    keyboard.append([InlineKeyboardButton(text="🔙 بازگشت به موضوعات", callback_data="menu_search_paper")])
                    await callback.message.answer(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
                else:
                    await callback.message.answer("❌ مقاله‌ای با این مشخصات یافت نشد.")

            elif data.startswith("kwmore_"):
                parts = data.replace("kwmore_", "").split("_")
                keyword_en = parts[0]
                page = int(parts[1])
                await callback.message.answer(f"⏳ در حال دریافت مقالات بیشتر برای «{keyword_en}» (صفحه {page})...")
                results = search_openalex(keyword_en, 2020, page=page)
                if results:
                    msg = f"📚 **نتایج جستجو برای «{keyword_en}» (صفحه {page}):**\n\n━━━━━━━━━━━━━━━\n\n"
                    for i, res in enumerate(results, 1):
                        msg += f"{i}. **{res['title']}**\n   👤 {res['author']} | 📅 {res['year']}\n   🔗 [مشاهده مقاله]({res['link']})\n\n"
                    msg += "━━━━━━━━━━━━━━━\n"
                    keyboard = [[InlineKeyboardButton(text="📄 مقالات بیشتر (صفحه بعد)", callback_data=f"kwmore_{keyword_en}_{page + 1}")]]
                    keyboard.append([InlineKeyboardButton(text="🔙 بازگشت به موضوعات", callback_data="menu_search_paper")])
                    await callback.message.answer(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
                else:
                    await callback.message.answer("❌ مقاله بیشتری یافت نشد.")

            elif data == "menu_cyclone":
                await callback.message.answer("⏳ در حال دریافت آخرین اطلاعات طوفان‌های حاره‌ای...")
                msg = "🌀 **وضعیت طوفان‌های حاره‌ای در خلیج فارس و دریای عمان:**\n\nبر اساس آخرین داده‌ها، در حال حاضر طوفان فعالی گزارش نشده است.\n\n🔗 https://www.rsmcnewdelhi.imd.gov.in/"
                await callback.message.answer(msg)

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

            # --- بخش اصلاح‌شده آلودگی هوا ---
            elif data == "menu_air_cities":
                await callback.message.answer("📍 شهر مورد نظر برای بررسی آلودگی هوا را انتخاب کنید:", reply_markup=get_city_menu("air"))
            elif data.startswith("air_"):
                city = data.replace("air_", "")
                lat, lon = CITIES[city]
                res = get_air_quality(lat, lon)  # <-- استفاده از تابع جدید
                if res and "hourly" in res:
                    pm25 = res["hourly"]["pm2_5"][0]
                    no2 = res["hourly"]["nitrogen_dioxide"][0]
                    msg = f"🏭 **آلودگی هوای {city}:**\n\n🔹 PM2.5: {round(pm25, 1) if pm25 is not None else 'نامشخص'} μg/m³\n🔹 NO₂: {round(no2, 1) if no2 is not None else 'نامشخص'} μg/m³"
                    await callback.message.answer(msg)
                else:
                    await callback.message.answer(f"❌ متاسفانه داده‌های آلودگی هوا برای {city} در دسترس نیست.")

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
                    msg = f"🌤️ **{city} (فردا):**\n\n🌡️ دما: {round(d['temperature_2m_min'][1], 1)}° تا {round(d['temperature_2m_max'][1], 1)}°\n🌧️ بارش کل: {round(d['precipitation_sum'][1], 1) if d['precipitation_sum'][1] else 0} mm"
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
                await callback.message.answer("❌ متاسفانه در پردازش درخواست شما خطایی رخ داد.")
            except:
                pass

    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())