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
from marine_api import get_copernicus_sst, get_marine_data, degree_to_direction, get_wind_analysis

load_dotenv()

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

BALE_TOKEN = os.getenv("BALE_TOKEN")

# ==========================================
# ۱. دیکشنری‌های تفکیک‌شده (بدون تکرار)
# ==========================================
INLAND_REGIONS = {
    "شمال و شمال غرب": {"ساری": (36.5633, 53.0601), "بابل": (36.5513, 52.6789), "بابلسر": (36.7000, 52.6500), "رشت": (37.2808, 49.5832), "بندر انزلی": (37.4720, 49.4630), "نوشهر": (36.6500, 51.5000), "اردبیل": (38.2498, 48.2933), "تبریز": (38.0800, 46.2919)},
    "مرکز": {"تهران": (35.6892, 51.3890), "اصفهان": (32.6546, 51.6680), "یزد": (31.8974, 54.3569), "قم": (34.6416, 50.8746), "کرمانشاه": (34.3142, 47.0650)},
    "جنوب و جنوب شرق": {"شیراز": (29.5918, 52.5837), "بندرعباس": (27.1832, 56.2666), "بوشهر": (28.9234, 50.8200), "زاهدان": (29.496, 60.862), "مکران": (25.5000, 59.5000)}
}

PERSIAN_GULF_CITIES = {"بندرعباس": (27.1832, 56.2666), "بوشهر": (28.9234, 50.8200), "بندر لنگه": (26.5500, 54.8800), "خارک": (29.2500, 50.3300), "بندر ماهشهر": (30.5589, 49.1981), "بندر دیر": (27.7300, 51.5000)}
PERSIAN_GULF_ISLANDS = {"قشم": (26.9500, 56.2700), "کیش": (26.5300, 53.9800), "هرمز": (27.0900, 56.4500), "لارک": (26.8500, 56.3500), "هنگام": (26.6500, 55.8800), "سی‌ری": (25.9000, 54.5300)}
OMAN_SEA_CITIES = {"چابهار": (25.2900, 60.6430), "جاسک": (25.6439, 57.7744), "کنارک": (25.3600, 60.3800)}
CASPIAN_CITIES = {"بندر انزلی": (37.4720, 49.4630), "بابلسر": (36.7000, 52.6500), "نوشهر": (36.6500, 51.5000), "چالوس": (36.6500, 51.4200), "آستارا": (38.4200, 48.8700), "گرگان (ساحل)": (36.8800, 54.0000)}

ALL_CITIES = {}
for region_cities in INLAND_REGIONS.values(): ALL_CITIES.update(region_cities)
ALL_CITIES.update(CASPIAN_CITIES); ALL_CITIES.update(PERSIAN_GULF_CITIES); ALL_CITIES.update(PERSIAN_GULF_ISLANDS); ALL_CITIES.update(OMAN_SEA_CITIES)

KEYWORD_TOPICS = [("تغییرات اقلیمی", "climate change"), ("ال نینو", "El Nino"), ("گرمایش جهانی", "global warming"), ("مرجان‌های خلیج فارس", "Persian Gulf coral"), ("گرد و غبار", "dust storm"), ("آلودگی هوا", "air pollution"), ("طوفان حاره‌ای", "tropical cyclone"), ("بالا آمدن سطح آب دریا", "sea level rise"), ("خشکسالی", "drought"), ("انرژی‌های تجدیدپذیر", "renewable energy")]

# --- توابع دریافت داده ---
def get_hourly_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "hourly": "temperature_2m,precipitation,weather_code,wind_speed_10m", "forecast_days": 3, "timezone": "Asia/Tehran"}
    try: return requests.get(url, params=params, timeout=30).json()
    except: return None

def get_dust_data(lat, lon):
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {"latitude": lat, "longitude": lon, "hourly": "dust,pm10", "forecast_days": 1, "timezone": "Asia/Tehran"}
    try: return requests.get(url, params=params, timeout=30).json()
    except: return None

def get_air_quality(lat, lon):
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {"latitude": lat, "longitude": lon, "hourly": "pm2_5,nitrogen_dioxide,ozone", "forecast_days": 1, "timezone": "Asia/Tehran"}
    try: return requests.get(url, params=params, timeout=30).json()
    except: return None

def search_openalex(keyword, year_from=2020, page=1):
    url = "https://api.openalex.org/works"
    params = {"search": keyword, "filter": f"from_publication_date:{year_from}-01-01", "sort": "relevance_score:desc", "per_page": 5, "page": page}
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        return [{"title": w.get("title", "بدون عنوان"), "year": w.get("publication_year", "نامشخص"), "link": w.get("doi") or w.get("id", ""), "author": w.get("authorships", [{}])[0].get("author", {}).get("display_name", "نامشخص")} for w in data.get("results", [])]
    except: return []

# --- منوها ---
def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌤️ آب و هوای شهرها", callback_data="menu_weather")],
        [InlineKeyboardButton(text="🚨 وضعیت طوفان", callback_data="menu_storm_cities")],
        [InlineKeyboardButton(text="🌫️ وضعیت گرد و خاک", callback_data="menu_dust_cities")],
        [InlineKeyboardButton(text="🏭 آلودگی هوا", callback_data="menu_air_cities")],
        [InlineKeyboardButton(text="📚 جستجوی مقاله", callback_data="menu_search_paper")],
        [InlineKeyboardButton(text="🌀 طوفان‌های حاره‌ای", callback_data="menu_cyclone")],
        [InlineKeyboardButton(text="🌊 خلیج فارس", callback_data="sea_gulf"), InlineKeyboardButton(text="🌊 دریای عمان", callback_data="sea_oman")],
        [InlineKeyboardButton(text="🌊 دریای خزر", callback_data="sea_caspian")],
    ])

def get_region_menu(prefix):
    kb = [[InlineKeyboardButton(text=region, callback_data=f"{prefix}_region_{region}")] for region in INLAND_REGIONS.keys()]
    kb.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_city_menu(prefix, city_dict):
    kb = []
    cities = list(city_dict.keys())
    for i in range(0, len(cities), 2):
        row = [InlineKeyboardButton(text=cities[i], callback_data=f"{prefix}_{cities[i]}")]
        if i + 1 < len(cities): row.append(InlineKeyboardButton(text=cities[i+1], callback_data=f"{prefix}_{cities[i+1]}"))
        kb.append(row)
    kb.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_keyword_menu():
    kb = []
    for i in range(0, len(KEYWORD_TOPICS), 2):
        row = [InlineKeyboardButton(text=KEYWORD_TOPICS[i][0], callback_data=f"kw_{KEYWORD_TOPICS[i][1]}")]
        if i + 1 < len(KEYWORD_TOPICS): row.append(InlineKeyboardButton(text=KEYWORD_TOPICS[i+1][0], callback_data=f"kw_{KEYWORD_TOPICS[i+1][1]}"))
        kb.append(row)
    kb.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- تابع دریاها (بدون کلروفیل) ---
async def send_marine_report(callback, city_name, lat, lon):
    try:
        await callback.message.edit_text(f"⏳ در حال دریافت داده‌های {city_name}...")
        sst = None
        try: sst = get_copernicus_sst(lat, lon)
        except Exception as e: print(f"SST Error {city_name}: {e}")
        
        marine_res = get_marine_data(lat, lon)
        msg = f"🌊 **{city_name}** 🌊\n\n"
        if sst is not None: msg += f"🌡️ دمای سطح آب (Copernicus): {sst} °C\n"
        if sst is None: msg += "⚠️ دمای سطح آب در دسترس نیست.\n"
        
        if marine_res and "hourly" in marine_res:
            h = marine_res["hourly"]
            wave_val = round(h['wave_height'][0], 2) if h['wave_height'][0] else 0
            wave_dir = h['wave_direction'][0] if h['wave_direction'][0] else 0
            wave_period = round(h['wave_period'][0], 1) if h['wave_period'][0] else 0
            current_vel = round(h['ocean_current_velocity'][0], 1) if h['ocean_current_velocity'][0] else 0
            wind_speed = round(h.get('wind_speed_10m', [0])[0], 1) if h.get('wind_speed_10m') else 0
            wind_dir = h.get('wind_direction_10m', [0])[0] if h.get('wind_direction_10m') else 0
            wind_analysis = get_wind_analysis(city_name, wind_dir)
            
            msg += f"\n📏 **موج (Open-Meteo):**\n   ارتفاع: {wave_val} متر\n   جهت: {degree_to_direction(wave_dir)} ({wave_dir}°)\n   دوره: {wave_period} ثانیه\n   جریان: {current_vel} km/h\n"
            msg += f"\n💨 **باد (Open-Meteo):**\n   سرعت: {wind_speed} km/h\n   جهت: {wind_analysis}\n"
            if wave_val >= 3: msg += "\n🚨 **طوفان دریایی:** تردد ممنوع."
            elif wave_val >= 1.5: msg += "\n⚠️ **متلاطم:** احتیاط کنید."
            else: msg += "\n🌊 **آرام:** مناسب برای تفریحات."
        else:
            msg += "\n⚠️ داده‌های موج در دسترس نیست."
        await callback.message.edit_text(msg, reply_markup=get_main_menu())
    except Exception as e:
        await callback.message.edit_text(f"❌ خطا در دریافت داده‌های {city_name}.", reply_markup=get_main_menu())
        print(f"Marine Error {city_name}: {e}")

async def main():
    print("=" * 60 + "\nربات جامع اقلیم روشن شد...\n" + "=" * 60)
    bot = Bot(token=BALE_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher()

    @dp.message()
    async def on_message(message: Message):
        await message.answer("👋 **به داشبورد اقلیم خوش آمدید.**", reply_markup=get_main_menu())

    @dp.callback_query()
    async def on_callback(callback: CallbackQuery):
        data = callback.data
        try:
            if data == "menu_main": await callback.message.edit_text("منوی اصلی:", reply_markup=get_main_menu())
            
            # --- بخش مقالات ---
            elif data == "menu_search_paper": await callback.message.edit_text("📚 موضوع مورد نظر را انتخاب کنید:", reply_markup=get_keyword_menu())
            elif data.startswith("kw_") and not data.startswith("kwmore_"):
                kw = data.replace("kw_", ""); await callback.message.edit_text(f"⏳ جستجو برای «{kw}»...")
                res = search_openalex(kw, 2020, 1)
                if res:
                    msg = f"📚 **نتایج «{kw}» (صفحه ۱):**\n\n"
                    for i, r in enumerate(res, 1): msg += f"{i}. **{r['title']}**\n   👤 {r['author']} | 📅 {r['year']}\n   🔗 [لینک]({r['link']})\n\n"
                    kb = [[InlineKeyboardButton(text="📄 بیشتر", callback_data=f"kwmore_{kw}_2")], [InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu_search_paper")]]
                    await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            elif data.startswith("kwmore_"):
                parts = data.replace("kwmore_", "").split("_"); kw, page = parts[0], int(parts[1])
                await callback.message.edit_text(f"⏳ جستجو برای «{kw}» (صفحه {page})...")
                res = search_openalex(kw, 2020, page)
                if res:
                    msg = f"📚 **نتایج «{kw}» (صفحه {page}):**\n\n"
                    for i, r in enumerate(res, 1): msg += f"{i}. **{r['title']}**\n   👤 {r['author']} | 📅 {r['year']}\n   🔗 [لینک]({r['link']})\n\n"
                    kb = [[InlineKeyboardButton(text="📄 بیشتر", callback_data=f"kwmore_{kw}_{page+1}")], [InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu_search_paper")]]
                    await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

            elif data == "menu_cyclone": await callback.message.edit_text("🌀 **طوفان‌های حاره‌ای:**\n\nدر حال حاضر طوفان فعالی گزارش نشده است.\n🔗 https://www.rsmcnewdelhi.imd.gov.in/", reply_markup=get_main_menu())
            
            # ==========================================
            # منوهای منطقه‌ای (طوفان، گرد و خاک، آلودگی، آب و هوا)
            # ==========================================
            elif data == "menu_storm_cities": await callback.message.edit_text("📍 منطقه مورد نظر را انتخاب کنید:", reply_markup=get_region_menu("storm"))
            elif data.startswith("storm_region_"):
                region = data.replace("storm_region_", "")
                if region in INLAND_REGIONS: await callback.message.edit_text(f"📍 شهر در منطقه {region}:", reply_markup=get_city_menu("storm", INLAND_REGIONS[region]))
            elif data.startswith("storm_"):
                city = data.replace("storm_", "")
                if city in ALL_CITIES:
                    res = get_hourly_weather(*ALL_CITIES[city])
                    if res and "hourly" in res:
                        h = res["hourly"]; max_wind = max(h['wind_speed_10m'][:24]) if h.get('wind_speed_10m') else 0
                        analysis = "🚨 خطرناک" if max_wind > 60 else "⚠️ هشدار" if max_wind > 40 else "🌬️ نسیم" if max_wind > 20 else "✅ آرام"
                        msg = f"🚨 **طوفان {city}:**\n\n💨 حداکثر باد (۲۴h): {round(max_wind, 1)} km/h\n📌 {analysis}"
                        await callback.message.edit_text(msg, reply_markup=get_main_menu())

            elif data == "menu_dust_cities": await callback.message.edit_text("📍 منطقه مورد نظر را انتخاب کنید:", reply_markup=get_region_menu("dust"))
            elif data.startswith("dust_region_"):
                region = data.replace("dust_region_", "")
                if region in INLAND_REGIONS: await callback.message.edit_text(f"📍 شهر در منطقه {region}:", reply_markup=get_city_menu("dust", INLAND_REGIONS[region]))
            elif data.startswith("dust_"):
                city = data.replace("dust_", "")
                if city in ALL_CITIES:
                    res = get_dust_data(*ALL_CITIES[city])
                    if res and "hourly" in res:
                        dust = res["hourly"]["dust"][0]; pm10 = res["hourly"]["pm10"][0]
                        analysis = "🔴 هشدار" if dust and dust > 50 else "🟡 متوسط" if dust and dust > 20 else "🟢 پاک"
                        msg = f"🌫️ **گرد و خاک {city}:**\n\n🌪️ Dust: {round(dust, 1) if dust else 'نامشخص'} | 💨 PM10: {round(pm10, 1) if pm10 else 'نامشخص'}\n📌 {analysis}"
                        await callback.message.edit_text(msg, reply_markup=get_main_menu())

            elif data == "menu_air_cities": await callback.message.edit_text("📍 منطقه مورد نظر را انتخاب کنید:", reply_markup=get_region_menu("air"))
            elif data.startswith("air_region_"):
                region = data.replace("air_region_", "")
                if region in INLAND_REGIONS: await callback.message.edit_text(f"📍 شهر در منطقه {region}:", reply_markup=get_city_menu("air", INLAND_REGIONS[region]))
            elif data.startswith("air_"):
                city = data.replace("air_", "")
                if city in ALL_CITIES:
                    res = get_air_quality(*ALL_CITIES[city])
                    if res and "hourly" in res:
                        pm25 = res["hourly"]["pm2_5"][0]
                        if pm25 is None: status = "نامشخص"
                        elif pm25 < 12: status = "پاک ✅"
                        elif pm25 < 35.5: status = "قابل قبول 🟡"
                        elif pm25 < 55.5: status = "ناسالم برای گروه‌های حساس 🟠"
                        elif pm25 < 150.5: status = "ناسالم 🔴"
                        else: status = "بسیار ناسالم ⛔"
                        msg = f"🏭 **آلودگی هوای {city}:**\n\n🔹 PM2.5: {round(pm25, 1) if pm25 else 'نامشخص'} μg/m³\n📊 {status}"
                        await callback.message.edit_text(msg, reply_markup=get_main_menu())

            elif data == "menu_weather": await callback.message.edit_text("📍 منطقه مورد نظر را انتخاب کنید:", reply_markup=get_region_menu("weather"))
            elif data.startswith("weather_region_"):
                region = data.replace("weather_region_", "")
                if region in INLAND_REGIONS: await callback.message.edit_text(f"📍 شهر در منطقه {region}:", reply_markup=get_city_menu("w", INLAND_REGIONS[region]))
            elif data.startswith("w_"):
                city = data.replace("w_", "")
                if city in ALL_CITIES:
                    res = get_hourly_weather(*ALL_CITIES[city])
                    if res and "hourly" in res:
                        h = res["hourly"]; msg = f"🌤️ **آب‌وهوای {city} (ساعتی - ۲ روز):**\n\n"
                        for i in range(0, 48, 2): # هر ۲ ساعت برای ۲ روز
                            if i < len(h['time']):
                                t = h['temperature_2m'][i]; rain = h['precipitation'][i]
                                w = "آفتابی" if h['weather_code'][i] == 0 else "ابری" if h['weather_code'][i] in [1,2,3] else "بارانی" if h['weather_code'][i] > 50 else "برفی"
                                msg += f"🕐 {h['time'][i][11:16]} | 🌡️ {round(t, 1)}° | {w} | 🌧️ {round(rain, 1)} mm\n"
                        await callback.message.edit_text(msg, reply_markup=get_main_menu())

            # --- دریاها ---
            elif data == "sea_gulf": await callback.message.edit_text("📍 شهر در خلیج فارس:", reply_markup=get_city_menu("gulf", {**PERSIAN_GULF_CITIES, **PERSIAN_GULF_ISLANDS}))
            elif data.startswith("gulf_"):
                city = data.replace("gulf_", ""); all_gulf = {**PERSIAN_GULF_CITIES, **PERSIAN_GULF_ISLANDS}
                if city in all_gulf: await send_marine_report(callback, city, *all_gulf[city])
            elif data == "sea_oman": await callback.message.edit_text("📍 شهر در دریای عمان:", reply_markup=get_city_menu("oman", OMAN_SEA_CITIES))
            elif data.startswith("oman_"):
                city = data.replace("oman_", "")
                if city in OMAN_SEA_CITIES: await send_marine_report(callback, city, *OMAN_SEA_CITIES[city])
            elif data == "sea_caspian": await callback.message.edit_text("📍 شهر در دریای خزر:", reply_markup=get_city_menu("caspian", CASPIAN_CITIES))
            elif data.startswith("caspian_"):
                city = data.replace("caspian_", "")
                if city in CASPIAN_CITIES: await send_marine_report(callback, city, *CASPIAN_CITIES[city])
        except Exception as e:
            print(f"Error: {e}")
            if "message is not modified" in str(e).lower(): pass
            else:
                try: await callback.message.answer("❌ خطایی رخ داد.", reply_markup=get_main_menu())
                except: pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())