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
    params = {"latitude": lat, "longitude": lon, "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,rain_sum,snowfall_sum,weather_code,wind_speed_10m_max", "forecast_days": 2, "timezone": "Asia/Tehran"}
    try: return requests.get(url, params=params, timeout=30).json()
    except: return None

# --- تابع جدید برای دریافت گرد و خاک از API کیفیت هوا ---
def get_dust_data(lat, lon):
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "dust,pm10",
        "forecast_days": 1,
        "timezone": "Asia/Tehran"
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error fetching dust: {e}")
        return None

def get_air_quality(lat, lon):
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {"latitude": lat, "longitude": lon, "hourly": "pm2_5,nitrogen_dioxide,ozone", "forecast_days": 1, "timezone": "Asia/Tehran"}
    try: return requests.get(url, params=params, timeout=30).json()
    except: return None

def get_marine_data(lat, lon):
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {"latitude": lat, "longitude": lon, "hourly": "wave_height,sea_surface_temperature", "forecast_days": 2, "timezone": "Asia/Tehran"}
    try: return requests.get(url, params=params, timeout=30).json()
    except: return None

def search_openalex(keyword, year_from=2020, page=1):
    url = "https://api.openalex.org/works"
    params = {"search": keyword, "filter": f"from_publication_date:{year_from}-01-01", "sort": "relevance_score:desc", "per_page": 5, "page": page}
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        results = []
        for work in data.get("results", []):
            results.append({
                "title": work.get("title", "بدون عنوان"),
                "year": work.get("publication_year", "نامشخص"),
                "link": work.get("doi") or work.get("id", ""),
                "author": work.get("authorships", [{}])[0].get("author", {}).get("display_name", "نامشخص")
            })
        return results
    except: return []

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

    def get_city_menu(prefix):
        kb = []
        cities = list(CITIES.keys())
        for i in range(0, len(cities), 2):
            row = [InlineKeyboardButton(text=cities[i], callback_data=f"{prefix}_{cities[i]}")]
            if i + 1 < len(cities):
                row.append(InlineKeyboardButton(text=cities[i+1], callback_data=f"{prefix}_{cities[i+1]}"))
            kb.append(row)
        kb.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu_main")])
        return InlineKeyboardMarkup(inline_keyboard=kb)

    def get_keyword_menu():
        kb = []
        for i in range(0, len(KEYWORD_TOPICS), 2):
            row = [InlineKeyboardButton(text=KEYWORD_TOPICS[i][0], callback_data=f"kw_{KEYWORD_TOPICS[i][1]}")]
            if i + 1 < len(KEYWORD_TOPICS):
                row.append(InlineKeyboardButton(text=KEYWORD_TOPICS[i+1][0], callback_data=f"kw_{KEYWORD_TOPICS[i+1][1]}"))
            kb.append(row)
        kb.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu_main")])
        return InlineKeyboardMarkup(inline_keyboard=kb)

    @dp.message()
    async def on_message(message: Message):
        await message.answer("👋 **به داشبورد اقلیم خوش آمدید.**", reply_markup=get_main_menu())

    @dp.callback_query()
    async def on_callback(callback: CallbackQuery):
        data = callback.data
        try: await callback.answer()
        except: pass

        try:
            if data == "menu_main":
                await callback.message.answer("منوی اصلی:", reply_markup=get_main_menu())

            # --- مقالات ---
            elif data == "menu_search_paper":
                await callback.message.answer("📚 موضوع مورد نظر را انتخاب کنید:", reply_markup=get_keyword_menu())
            elif data.startswith("kw_") and not data.startswith("kwmore_"):
                kw = data.replace("kw_", "")
                await callback.message.answer(f"⏳ جستجو برای «{kw}»...")
                res = search_openalex(kw, 2020, 1)
                if res:
                    msg = f"📚 **نتایج «{kw}» (صفحه ۱):**\n\n"
                    for i, r in enumerate(res, 1):
                        msg += f"{i}. **{r['title']}**\n   👤 {r['author']} | 📅 {r['year']}\n   🔗 [لینک]({r['link']})\n\n"
                    kb = [[InlineKeyboardButton(text="📄 بیشتر", callback_data=f"kwmore_{kw}_2")], [InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu_search_paper")]]
                    await callback.message.answer(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            elif data.startswith("kwmore_"):
                parts = data.replace("kwmore_", "").split("_")
                kw, page = parts[0], int(parts[1])
                res = search_openalex(kw, 2020, page)
                if res:
                    msg = f"📚 **نتایج «{kw}» (صفحه {page}):**\n\n"
                    for i, r in enumerate(res, 1):
                        msg += f"{i}. **{r['title']}**\n   👤 {r['author']} | 📅 {r['year']}\n   🔗 [لینک]({r['link']})\n\n"
                    kb = [[InlineKeyboardButton(text="📄 بیشتر", callback_data=f"kwmore_{kw}_{page+1}")], [InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu_search_paper")]]
                    await callback.message.answer(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

            # --- طوفان حاره‌ای ---
            elif data == "menu_cyclone":
                await callback.message.answer("🌀 **طوفان‌های حاره‌ای:**\n\nدر حال حاضر طوفان فعالی در خلیج فارس و دریای عمان گزارش نشده است.\n🔗 https://www.rsmcnewdelhi.imd.gov.in/")

            # --- طوفان شهرها ---
            elif data == "menu_storm_cities":
                await callback.message.answer("📍 شهر را انتخاب کنید:", reply_markup=get_city_menu("storm"))
            elif data.startswith("storm_"):
                city = data.replace("storm_", "")
                res = get_full_weather(*CITIES[city])
                if res and "daily" in res:
                    wind = res["daily"]["wind_speed_10m_max"][1]
                    wind_val = round(wind, 1) if wind else 0
                    if wind_val > 60: analysis = "🚨 **خطرناک:** سرعت باد بالای ۶۰ کیلومتر است. از تردد در فضای باز خودداری کنید."
                    elif wind_val > 40: analysis = "⚠️ **هشدار:** باد نسبتاً شدید است. احتمال گرد و خاک و اختلال در تردد وجود دارد."
                    elif wind_val > 20: analysis = "🌬️ **نسیم:** باد ملایم تا متوسط است."
                    else: analysis = "✅ **آرام:** هوا کاملاً آرام است."
                    msg = f"🚨 **وضعیت طوفان {city}:**\n\n💨 سرعت باد: {wind_val} km/h\n\n📌 **تحلیل:** {analysis}"
                    await callback.message.answer(msg)

            # --- گرد و خاک (اصلاح‌شده با API جدید) ---
            elif data == "menu_dust_cities":
                await callback.message.answer("📍 شهر را انتخاب کنید:", reply_markup=get_city_menu("dust"))
            elif data.startswith("dust_"):
                city = data.replace("dust_", "")
                # استفاده از تابع جدید get_dust_data
                res = get_dust_data(*CITIES[city])
                if res and "hourly" in res:
                    dust = res["hourly"]["dust"][0]
                    pm10 = res["hourly"]["pm10"][0]
                    if dust is not None and dust > 50: analysis = "🔴 **هشدار:** گرد و خاک زیاد است. برای بیماران تنفسی مضر است."
                    elif dust is not None and dust > 20: analysis = "🟡 **متوسط:** گرد و خاک ملایم وجود دارد. افراد حساس ماسک بزنند."
                    else: analysis = "🟢 **پاک:** هوا از نظر گرد و خاک تمیز است."
                    msg = f"🌫️ **گرد و خاک {city}:**\n\n🌪️ Dust: {round(dust, 1) if dust is not None else 'نامشخص'} μg/m³\n💨 PM10: {round(pm10, 1) if pm10 is not None else 'نامشخص'} μg/m³\n\n📌 **تحلیل:** {analysis}"
                    await callback.message.answer(msg)
                else:
                    await callback.message.answer(f"❌ داده‌های گرد و خاک برای {city} در دسترس نیست.")

            # --- آلودگی هوا ---
            elif data == "menu_air_cities":
                await callback.message.answer("📍 شهر را انتخاب کنید:", reply_markup=get_city_menu("air"))
            elif data.startswith("air_"):
                city = data.replace("air_", "")
                res = get_air_quality(*CITIES[city])
                if res and "hourly" in res:
                    pm25 = res["hourly"]["pm2_5"][0]
                    no2 = res["hourly"]["nitrogen_dioxide"][0]
                    ozone = res["hourly"]["ozone"][0]
                    if pm25 is None: status, advice = "نامشخص", "داده‌ای نیست."
                    elif pm25 < 12: status, advice = "پاک ✅", "هوا کاملاً سالم است."
                    elif pm25 < 35.5: status, advice = "قابل قبول 🟡", "هوا مناسب است."
                    elif pm25 < 55.5: status, advice = "ناسالم برای گروه‌های حساس 🟠", "سالمندان و کودکان فعالیت در فضای باز را کاهش دهند."
                    elif pm25 < 150.5: status, advice = "ناسالم 🔴", "همه افراد اثرات سلامتی را تجربه می‌کنند."
                    else: status, advice = "بسیار ناسالم ⛔", "همه افراد باید در خانه بمانند."
                    msg = f"🏭 **آلودگی هوای {city}:**\n\n🔹 PM2.5: {round(pm25, 1) if pm25 is not None else 'نامشخص'} μg/m³\n🔹 NO₂: {round(no2, 1) if no2 is not None else 'نامشخص'} μg/m³\n"
                    if ozone is not None: msg += f"🔹 ازن (O₃): {round(ozone, 1)} μg/m³\n"
                    msg += f"\n📊 **وضعیت:** {status}\n📌 **توصیه:** {advice}"
                    await callback.message.answer(msg)

            # --- آب و هوا ---
            elif data == "menu_weather":
                await callback.message.answer("📍 شهر را انتخاب کنید:", reply_markup=get_city_menu("w"))
            elif data.startswith("w_"):
                city = data.replace("w_", "")
                res = get_full_weather(*CITIES[city])
                if res and "daily" in res:
                    d = res["daily"]
                    tmin = round(d['temperature_2m_min'][1], 1) if d['temperature_2m_min'][1] is not None else 0
                    tmax = round(d['temperature_2m_max'][1], 1) if d['temperature_2m_max'][1] is not None else 0
                    rain = round(d['precipitation_sum'][1], 1) if d['precipitation_sum'][1] else 0
                    if rain == 0: analysis = "☀️ **خشک:** بارشی پیش‌بینی نمی‌شود."
                    elif rain < 5: analysis = "🌦️ **بارش خفیف:** احتمال باران پراکنده."
                    elif rain < 15: analysis = "🌧️ **بارش متوسط:** باران قابل توجهی می‌بارد."
                    else: analysis = "⛈️ **بارش شدید:** احتمال سیل و آب‌گرفتگی."
                    msg = f"🌤️ **آب‌وهوای {city} (فردا):**\n\n🌡️ دما: {tmin}° تا {tmax}°\n🌧️ بارش: {rain} mm\n\n📌 **تحلیل:** {analysis}"
                    await callback.message.answer(msg)

            # --- بارش ---
            elif data == "menu_rain":
                await callback.message.answer("📍 شهر را انتخاب کنید:", reply_markup=get_city_menu("rain"))
            elif data.startswith("rain_"):
                city = data.replace("rain_", "")
                res = get_full_weather(*CITIES[city])
                if res and "daily" in res:
                    d = res["daily"]
                    rain = d['rain_sum'][1] if d['rain_sum'][1] else 0
                    snow = d['snowfall_sum'][1] if d['snowfall_sum'][1] else 0
                    if rain == 0 and snow == 0: analysis = "☀️ **بدون بارش:** آسمان صاف یا ابری است."
                    elif rain > 0 and snow > 0: analysis = "🌨️ **بارش مختلط:** باران و برف توأم."
                    elif snow > 0: analysis = "❄️ **برفی:** لباس گرم و زنجیر چرخ لازم است."
                    else: analysis = "🌧️ **بارانی:** لباس ضدآب همراه داشته باشید."
                    msg = f"🌧️ **میزان بارش {city} (فردا):**\n\n☔ باران: {round(rain, 1)} mm\n❄️ برف: {round(snow, 1)} cm\n\n📌 **تحلیل:** {analysis}"
                    await callback.message.answer(msg)

            # --- دریاها ---
            elif data == "sea_gulf":
                res = get_marine_data(27.0, 51.0)
                if res and "hourly" in res:
                    h = res["hourly"]
                    wave_val = round(h['wave_height'][0], 2) if h['wave_height'][0] else 0
                    sst = h['sea_surface_temperature'][0]
                    if wave_val >= 3: analysis = "🚨 **طوفان دریایی:** تردد شناورهای سبک ممنوع."
                    elif wave_val >= 1.5: analysis = "⚠️ **متلاطم:** شناگران احتیاط کنند."
                    else: analysis = "🌊 **آرام:** برای تفریحات آبی مناسب است."
                    msg = f"🌊 **خلیج فارس:**\n\n📏 موج: {wave_val} متر\n🌡️ دمای آب: {round(sst, 1) if sst else 'نامشخص'} °C\n\n📌 {analysis}"
                    await callback.message.answer(msg)

            elif data == "sea_oman":
                res = get_marine_data(25.0, 58.0)
                if res and "hourly" in res:
                    h = res["hourly"]
                    wave_val = round(h['wave_height'][0], 2) if h['wave_height'][0] else 0
                    sst = h['sea_surface_temperature'][0]
                    if wave_val >= 3: analysis = "🚨 **طوفان دریایی:** تردد ممنوع."
                    elif wave_val >= 1.5: analysis = "⚠️ **متلاطم:** احتیاط کنید."
                    else: analysis = "🌊 **آرام:** دریا آرام است."
                    msg = f"🌊 **دریای عمان:**\n\n📏 موج: {wave_val} متر\n🌡️ دمای آب: {round(sst, 1) if sst else 'نامشخص'} °C\n\n📌 {analysis}"
                    await callback.message.answer(msg)

        except Exception as e:
            print(f"Error: {e}")
            try: await callback.message.answer("❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.")
            except: pass

    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())