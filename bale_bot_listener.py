import asyncio
import logging
import sys
import os
import requests
from marine_api import get_copernicus_sst, get_copernicus_chlorophyll, get_marine_data, degree_to_direction
from baleio import Bot, Dispatcher, md, types
from baleio.client.default import DefaultBotProperties
from baleio.enums import ParseMode
from baleio.types import Message, CallbackQuery
from baleio.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import copernicusmarine
from datetime import datetime, timedelta

load_dotenv()

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

BALE_TOKEN = os.getenv("BALE_TOKEN")
COPERNICUS_USER = os.getenv("COPERNICUS_USER")
COPERNICUS_PASS = os.getenv("COPERNICUS_PASS")

# ==========================================
# ۱. دسته‌بندی شهرهای غیرساحلی (منطقه‌ای)
# ==========================================
INLAND_REGIONS = {
    "شمال و شمال غرب": {
        "ساری": (36.5633, 53.0601), "بابل": (36.5513, 52.6789), "بابلسر": (36.7000, 52.6500),
        "رشت": (37.2808, 49.5832), "بندر انزلی": (37.4720, 49.4630), "نوشهر": (36.6500, 51.5000),
        "اردبیل": (38.2498, 48.2933), "تبریز": (38.0800, 46.2919)
    },
    "مرکز": {
        "تهران": (35.6892, 51.3890), "اصفهان": (32.6546, 51.6680), "یزد": (31.8974, 54.3569),
        "قم": (34.6416, 50.8746), "کرمانشاه": (34.3142, 47.0650)
    },
    "جنوب و جنوب شرق": {
        "شیراز": (29.5918, 52.5837), "بندرعباس": (27.1832, 56.2666), "بوشهر": (28.9234, 50.8200),
        "زاهدان": (29.496, 60.862), "مکران": (25.5000, 59.5000)
    }
}

# ==========================================
# ۲. شهرهای ساحلی و جزایر (تفکیک شده)
# ==========================================
CASPIAN_CITIES = {
    "بندر انزلی": (37.4720, 49.4630), "بابلسر": (36.7000, 52.6500), "نوشهر": (36.6500, 51.5000),
    "چالوس": (36.6500, 51.4200), "آستارا": (38.4200, 48.8700), "گرگان (ساحل)": (36.8800, 54.0000)
}

PERSIAN_GULF_CITIES = {
    "بندرعباس": (27.1832, 56.2666), "بوشهر": (28.9234, 50.8200), "بندر لنگه": (26.5500, 54.8800),
    "خارک": (29.2500, 50.3300), "بندر ماهشهر": (30.5589, 49.1981), "بندر دیر": (27.7300, 51.5000)
}

OMAN_SEA_CITIES = {
    "چابهار": (25.2900, 60.6430), "جاسک": (25.6439, 57.7744), "کنارک": (25.3600, 60.3800)
}

PERSIAN_GULF_ISLANDS = {
    "قشم": (26.9500, 56.2700), "کیش": (26.5300, 53.9800), "هرمز": (27.0900, 56.4500),
    "لارک": (26.8500, 56.3500), "هنگام": (26.6500, 55.8800), "سی‌ری": (25.9000, 54.5300)
}

# ساخت دیکشنری تخت از همه شهرها برای منوهای عمومی (طوفان، گرد و خاک و...)
ALL_CITIES = {}
for region_cities in INLAND_REGIONS.values():
    ALL_CITIES.update(region_cities)
ALL_CITIES.update(CASPIAN_CITIES)
ALL_CITIES.update(PERSIAN_GULF_CITIES)
ALL_CITIES.update(OMAN_SEA_CITIES)
ALL_CITIES.update(PERSIAN_GULF_ISLANDS)

KEYWORD_TOPICS = [
    ("تغییرات اقلیمی", "climate change"), ("ال نینو", "El Nino"),
    ("گرمایش جهانی", "global warming"), ("مرجان‌های خلیج فارس", "Persian Gulf coral"),
    ("گرد و غبار", "dust storm"), ("آلودگی هوا", "air pollution"),
    ("طوفان حاره‌ای", "tropical cyclone"), ("بالا آمدن سطح آب دریا", "sea level rise"),
    ("خشکسالی", "drought"), ("انرژی‌های تجدیدپذیر", "renewable energy")
]

# --- توابع هواشناسی (Open-Meteo) ---
def get_full_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,rain_sum,snowfall_sum,weather_code,wind_speed_10m_max",
        "forecast_days": 3, "timezone": "Asia/Tehran"
    }
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

def get_marine_data(lat, lon):
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "wave_height,wave_direction,wave_period,sea_surface_temperature,ocean_current_velocity",
        "forecast_days": 2, "past_days": 2, "timezone": "Asia/Tehran"
    }
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

# --- توابع Copernicus (داده‌های اقیانوسی) ---
def get_copernicus_sst(lat, lon):
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        ds = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m",
            variables=["thetao"],
            minimum_longitude=lon - 0.1, maximum_longitude=lon + 0.1,
            minimum_latitude=lat - 0.1, maximum_latitude=lat + 0.1,
            start_datetime=start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            end_datetime=end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            minimum_depth=0, maximum_depth=1,
            username=COPERNICUS_USER, password=COPERNICUS_PASS
        )
        sst = float(ds["thetao"].mean())
        return round(sst, 1)
    except Exception as e:
        print(f"Copernicus SST Error for {lat},{lon}: {e}")
        return None

def get_copernicus_chlorophyll(lat, lon):
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        ds = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_bgc_anfc_0.083deg_P1D-m", 
            variables=["chl"],
            minimum_longitude=lon - 0.1, maximum_longitude=lon + 0.1,
            minimum_latitude=lat - 0.1, maximum_latitude=lat + 0.1,
            start_datetime=start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            end_datetime=end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            minimum_depth=0, maximum_depth=1,
            username=COPERNICUS_USER, password=COPERNICUS_PASS
        )
        chl = float(ds["chl"].mean())
        return round(chl, 2)
    except Exception as e:
        print(f"Copernicus Chl Error for {lat},{lon}: {e}")
        return None

# --- توابع منو ---
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
        [InlineKeyboardButton(text="🌊 دریای خزر", callback_data="sea_caspian")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_city_menu(prefix, city_dict):
    kb = []
    cities = list(city_dict.keys())
    for i in range(0, len(cities), 2):
        row = [InlineKeyboardButton(text=cities[i], callback_data=f"{prefix}_{cities[i]}")]
        if i + 1 < len(cities):
            row.append(InlineKeyboardButton(text=cities[i+1], callback_data=f"{prefix}_{cities[i+1]}"))
        kb.append(row)
    kb.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_region_menu():
    kb = []
    for region in INLAND_REGIONS.keys():
        kb.append([InlineKeyboardButton(text=region, callback_data=f"region_{region}")])
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

# --- تابع کمکی برای ساخت پیام دریایی ---
async def send_marine_report(callback, city_name, lat, lon):
    await callback.message.edit_text(f"⏳ در حال دریافت داده‌های {city_name}...")
    
    sst = get_copernicus_sst(lat, lon)
    chl = get_copernicus_chlorophyll(lat, lon)
    marine_res = get_marine_data(lat, lon) # این تابع را از marine_api.py ایمپورت کردیم
    
    msg = f"🌊 **{city_name}** 🌊\n\n"
    if sst: msg += f"🌡️ دمای سطح آب (Copernicus): {sst} °C\n"
    if chl: msg += f"🟢 کلروفیل-a (Copernicus): {chl} mg/m³\n"
    
    if marine_res and "hourly" in marine_res:
        h = marine_res["hourly"]
        # داده‌های موج
        wave_val = round(h['wave_height'][0], 2) if h['wave_height'][0] else 0
        wave_dir = h['wave_direction'][0] if h['wave_direction'][0] else 0
        wave_period = round(h['wave_period'][0], 1) if h['wave_period'][0] else 0
        current_vel = round(h['ocean_current_velocity'][0], 1) if h['ocean_current_velocity'][0] else 0
        
        # داده‌های باد (جدید)
        wind_speed = round(h.get('wind_speed_10m', [0])[0], 1) if h.get('wind_speed_10m') else 0
        wind_dir = h.get('wind_direction_10m', [0])[0] if h.get('wind_direction_10m') else 0
        
        msg += f"\n📏 **موج (Open-Meteo):**\n"
        msg += f"   ارتفاع: {wave_val} متر\n"
        msg += f"   جهت: {degree_to_direction(wave_dir)} ({wave_dir}°)\n" # استفاده از تابع تبدیل
        msg += f"   دوره: {wave_period} ثانیه\n"
        msg += f"   جریان: {current_vel} km/h\n"
        
        msg += f"\n💨 **باد (Open-Meteo):**\n" # بخش باد اضافه شد
        msg += f"   سرعت: {wind_speed} km/h\n"
        msg += f"   جهت: {degree_to_direction(wind_dir)} ({wind_dir}°)\n"
        
        if wave_val >= 3: msg += "\n🚨 **طوفان دریایی:** تردد شناورهای سبک ممنوع."
        elif wave_val >= 1.5: msg += "\n⚠️ **متلاطم:** شناگران احتیاط کنند."
        else: msg += "\n🌊 **آرام:** برای تفریحات آبی مناسب است."
    else:
        msg += "\n⚠️ داده‌های موج در دسترس نیست."
    
    await callback.message.edit_text(msg, reply_markup=get_main_menu())

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
            if data == "menu_main":
                await callback.message.edit_text("منوی اصلی:", reply_markup=get_main_menu())

            elif data == "menu_search_paper":
                await callback.message.edit_text("📚 موضوع مورد نظر را انتخاب کنید:", reply_markup=get_keyword_menu())
            
            elif data.startswith("kw_") and not data.startswith("kwmore_"):
                kw = data.replace("kw_", "")
                await callback.message.edit_text(f"⏳ جستجو برای «{kw}»...")
                res = search_openalex(kw, 2020, 1)
                if res:
                    msg = f"📚 **نتایج «{kw}» (صفحه ۱):**\n\n"
                    for i, r in enumerate(res, 1):
                        msg += f"{i}. **{r['title']}**\n   👤 {r['author']} | 📅 {r['year']}\n   🔗 [لینک]({r['link']})\n\n"
                    kb = [[InlineKeyboardButton(text="📄 بیشتر", callback_data=f"kwmore_{kw}_2")], [InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu_search_paper")]]
                    await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            
            elif data.startswith("kwmore_"):
                parts = data.replace("kwmore_", "").split("_")
                kw, page = parts[0], int(parts[1])
                await callback.message.edit_text(f"⏳ جستجو برای «{kw}» (صفحه {page})...")
                res = search_openalex(kw, 2020, page)
                if res:
                    msg = f"📚 **نتایج «{kw}» (صفحه {page}):**\n\n"
                    for i, r in enumerate(res, 1):
                        msg += f"{i}. **{r['title']}**\n   👤 {r['author']} | 📅 {r['year']}\n   🔗 [لینک]({r['link']})\n\n"
                    kb = [[InlineKeyboardButton(text="📄 بیشتر", callback_data=f"kwmore_{kw}_{page+1}")], [InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu_search_paper")]]
                    await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

            elif data == "menu_cyclone":
                await callback.message.edit_text("🌀 **طوفان‌های حاره‌ای:**\n\nدر حال حاضر طوفان فعالی در خلیج فارس و دریای عمان گزارش نشده است.\n🔗 https://www.rsmcnewdelhi.imd.gov.in/", reply_markup=get_main_menu())

            # --- منوهای عمومی (شامل همه شهرها) ---
            elif data == "menu_storm_cities":
                await callback.message.edit_text("📍 شهر را انتخاب کنید:", reply_markup=get_city_menu("storm", ALL_CITIES))
            elif data.startswith("storm_"):
                city = data.replace("storm_", "")
                if city in ALL_CITIES:
                    res = get_full_weather(*ALL_CITIES[city])
                    if res and "daily" in res:
                        wind = res["daily"]["wind_speed_10m_max"][1]
                        wind_val = round(wind, 1) if wind else 0
                        if wind_val > 60: analysis = "🚨 **خطرناک:** سرعت باد بالای ۶۰ کیلومتر است."
                        elif wind_val > 40: analysis = "⚠️ **هشدار:** باد نسبتاً شدید است."
                        elif wind_val > 20: analysis = "🌬️ **نسیم:** باد ملایم است."
                        else: analysis = "✅ **آرام:** هوا آرام است."
                        msg = f"🚨 **وضعیت طوفان {city}:**\n\n💨 سرعت باد: {wind_val} km/h\n\n📌 **تحلیل:** {analysis}"
                        await callback.message.edit_text(msg, reply_markup=get_main_menu())

            elif data == "menu_dust_cities":
                await callback.message.edit_text("📍 شهر را انتخاب کنید:", reply_markup=get_city_menu("dust", ALL_CITIES))
            elif data.startswith("dust_"):
                city = data.replace("dust_", "")
                if city in ALL_CITIES:
                    res = get_dust_data(*ALL_CITIES[city])
                    if res and "hourly" in res:
                        dust = res["hourly"]["dust"][0]
                        pm10 = res["hourly"]["pm10"][0]
                        if dust is not None and dust > 50: analysis = "🔴 **هشدار:** گرد و خاک زیاد است."
                        elif dust is not None and dust > 20: analysis = "🟡 **متوسط:** گرد و خاک ملایم وجود دارد."
                        else: analysis = "🟢 **پاک:** هوا تمیز است."
                        msg = f"🌫️ **گرد و خاک {city}:**\n\n🌪️ Dust: {round(dust, 1) if dust is not None else 'نامشخص'} μg/m³\n💨 PM10: {round(pm10, 1) if pm10 is not None else 'نامشخص'} μg/m³\n\n📌 **تحلیل:** {analysis}"
                        await callback.message.edit_text(msg, reply_markup=get_main_menu())

            elif data == "menu_air_cities":
                await callback.message.edit_text("📍 شهر را انتخاب کنید:", reply_markup=get_city_menu("air", ALL_CITIES))
            elif data.startswith("air_"):
                city = data.replace("air_", "")
                if city in ALL_CITIES:
                    res = get_air_quality(*ALL_CITIES[city])
                    if res and "hourly" in res:
                        pm25 = res["hourly"]["pm2_5"][0]
                        no2 = res["hourly"]["nitrogen_dioxide"][0]
                        ozone = res["hourly"]["ozone"][0]
                        if pm25 is None: status, advice = "نامشخص", "داده‌ای نیست."
                        elif pm25 < 12: status, advice = "پاک ✅", "هوا کاملاً سالم است."
                        elif pm25 < 35.5: status, advice = "قابل قبول 🟡", "هوا مناسب است."
                        elif pm25 < 55.5: status, advice = "ناسالم برای گروه‌های حساس 🟠", "سالمندان و کودکان احتیاط کنند."
                        elif pm25 < 150.5: status, advice = "ناسالم 🔴", "همه افراد اثرات سلامتی را تجربه می‌کنند."
                        else: status, advice = "بسیار ناسالم ⛔", "همه افراد باید در خانه بمانند."
                        msg = f"🏭 **آلودگی هوای {city}:**\n\n🔹 PM2.5: {round(pm25, 1) if pm25 is not None else 'نامشخص'} μg/m³\n🔹 NO₂: {round(no2, 1) if no2 is not None else 'نامشخص'} μg/m³\n"
                        if ozone is not None: msg += f"🔹 ازن (O₃): {round(ozone, 1)} μg/m³\n"
                        msg += f"\n📊 **وضعیت:** {status}\n📌 **توصیه:** {advice}"
                        await callback.message.edit_text(msg, reply_markup=get_main_menu())

            # --- بخش هواشناسی (منطقه‌ای) ---
            elif data == "menu_weather":
                await callback.message.edit_text("📍 منطقه مورد نظر را انتخاب کنید:", reply_markup=get_region_menu())
            elif data.startswith("region_"):
                region = data.replace("region_", "")
                if region in INLAND_REGIONS:
                    await callback.message.edit_text(f"📍 شهر مورد نظر در منطقه {region} را انتخاب کنید:", reply_markup=get_city_menu("w", INLAND_REGIONS[region]))
            elif data.startswith("w_"):
                city = data.replace("w_", "")
                if city in ALL_CITIES:
                    res = get_full_weather(*ALL_CITIES[city])
                    if res and "daily" in res:
                        d = res["daily"]
                        msg = f"🌤️ **آب‌وهوای {city} (۳ روز آینده):**\n\n"
                        for i in range(3):
                            if i < len(d['time']):
                                tmin = round(d['temperature_2m_min'][i], 1) if d['temperature_2m_min'][i] is not None else 0
                                tmax = round(d['temperature_2m_max'][i], 1) if d['temperature_2m_max'][i] is not None else 0
                                rain = round(d['precipitation_sum'][i], 1) if d['precipitation_sum'][i] else 0
                                msg += f"📅 **روز {i+1}:**\n🌡️ دما: {tmin}° تا {tmax}°\n🌧️ بارش: {rain} mm\n\n"
                        await callback.message.edit_text(msg, reply_markup=get_main_menu())

            elif data == "menu_rain":
                await callback.message.edit_text("📍 منطقه مورد نظر را انتخاب کنید:", reply_markup=get_region_menu())
            elif data.startswith("rain_region_"):
                region = data.replace("rain_region_", "")
                if region in INLAND_REGIONS:
                    await callback.message.edit_text(f"📍 شهر مورد نظر در منطقه {region} را انتخاب کنید:", reply_markup=get_city_menu("rain", INLAND_REGIONS[region]))
            elif data.startswith("rain_"):
                city = data.replace("rain_", "")
                if city in ALL_CITIES:
                    res = get_full_weather(*ALL_CITIES[city])
                    if res and "daily" in res:
                        d = res["daily"]
                        rain = d['rain_sum'][1] if d['rain_sum'][1] else 0
                        snow = d['snowfall_sum'][1] if d['snowfall_sum'][1] else 0
                        if rain == 0 and snow == 0: analysis = "☀️ **بدون بارش:** آسمان صاف یا ابری است."
                        elif rain > 0 and snow > 0: analysis = "🌨️ **بارش مختلط:** باران و برف توأم."
                        elif snow > 0: analysis = "❄️ **برفی:** لباس گرم و زنجیر چرخ لازم است."
                        else: analysis = "🌧️ **بارانی:** لباس ضدآب همراه داشته باشید."
                        msg = f"🌧️ **میزان بارش {city} (فردا):**\n\n☔ باران: {round(rain, 1)} mm\n❄️ برف: {round(snow, 1)} cm\n\n📌 **تحلیل:** {analysis}"
                        await callback.message.edit_text(msg, reply_markup=get_main_menu())

            # --- بخش دریایی (تفکیک شده) ---
            elif data == "sea_gulf":
                await callback.message.edit_text("📍 منطقه مورد نظر در خلیج فارس را انتخاب کنید:", reply_markup=get_city_menu("gulf", {**PERSIAN_GULF_CITIES, **PERSIAN_GULF_ISLANDS}))
            elif data.startswith("gulf_"):
                city = data.replace("gulf_", "")
                all_gulf = {**PERSIAN_GULF_CITIES, **PERSIAN_GULF_ISLANDS}
                if city in all_gulf:
                    await send_marine_report(callback, city, *all_gulf[city])

            elif data == "sea_oman":
                await callback.message.edit_text("📍 شهر ساحلی دریای عمان را انتخاب کنید:", reply_markup=get_city_menu("oman", OMAN_SEA_CITIES))
            elif data.startswith("oman_"):
                city = data.replace("oman_", "")
                if city in OMAN_SEA_CITIES:
                    await send_marine_report(callback, city, *OMAN_SEA_CITIES[city])

            elif data == "sea_caspian":
                await callback.message.edit_text("📍 شهر ساحلی دریای خزر را انتخاب کنید:", reply_markup=get_city_menu("caspian", CASPIAN_CITIES))
            elif data.startswith("caspian_"):
                city = data.replace("caspian_", "")
                if city in CASPIAN_CITIES:
                    await send_marine_report(callback, city, *CASPIAN_CITIES[city])

        except Exception as e:
            print(f"Error: {e}")
            if "message is not modified" in str(e).lower() or "bad request" in str(e).lower():
                pass
            else:
                try: await callback.message.answer("❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.", reply_markup=get_main_menu())
                except: pass

    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())