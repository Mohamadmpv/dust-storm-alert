import asyncio
import logging
import sys
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# ==========================================
# ۱. دیکشنری‌های تفکیک‌شده (همانند بله)
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

KEYWORD_TOPICS = [("تغییرات اقلیمی", "climate change"), ("ال نینو", "El Nino"), ("گرمایش جهانی", "global warming"), ("مرجان‌های خلیج فارس", "Persian Gulf coral"), ("گرد و غبار", "dust storm"), ("آلودگی هوا", "air pollution"), ("طوفان حاره‌ای", "tropical cyclone"), ("بالا آمدن سطح آب دریا", "sea level rise"), ("خشکسالی", "drought"), ("انرژی‌های تجدیدپذیر", "renewable energy")]

# --- توابع دریافت داده ---
def get_hourly_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "hourly": "temperature_2m,precipitation,weather_code,wind_speed_10m,wind_direction_10m", "forecast_days": 3, "timezone": "Asia/Tehran"}
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
    params = {"latitude": lat, "longitude": lon, "hourly": "wave_height,wave_direction,wave_period,sea_surface_temperature,ocean_current_velocity", "forecast_days": 2, "past_days": 2, "timezone": "Asia/Tehran"}
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

# --- توابع تحلیل باد ---
def degree_to_direction(degree):
    if degree is None: return "نامشخص"
    if 337.5 <= degree or degree < 22.5: return "شمال"
    elif 22.5 <= degree < 67.5: return "شمال‌شرق"
    elif 67.5 <= degree < 112.5: return "شرق"
    elif 112.5 <= degree < 157.5: return "جنوب‌شرق"
    elif 157.5 <= degree < 202.5: return "جنوب"
    elif 202.5 <= degree < 247.5: return "جنوب‌غرب"
    elif 247.5 <= degree < 292.5: return "غرب"
    elif 292.5 <= degree < 337.5: return "شمال‌غرب"
    return "نامشخص"

def get_wind_analysis(city_name, degree):
    direction = degree_to_direction(degree)
    if city_name in ["بندر انزلی", "بابلسر", "نوشهر", "چالوس", "آستارا", "گرگان (ساحل)"]:
        if direction in ["شمال", "شمال‌غرب"]: return f"از سمت {direction} (منشأ: روسیه و قفقاز)"
        elif direction in ["جنوب", "جنوب‌شرق"]: return f"از سمت {direction} (منشأ: کوه‌های البرز)"
        elif direction == "غرب": return f"از سمت {direction} (منشأ: اروپا)"
    elif city_name in ["بندرعباس", "بوشهر", "بندر لنگه", "خارک", "بندر ماهشهر", "بندر دیر", "قشم", "کیش", "هرمز", "لارک", "هنگام", "سی‌ری"]:
        if direction in ["شمال", "شمال‌غرب"]: return f"از سمت {direction} (منشأ: عراق و سوریه)"
        elif direction in ["جنوب", "جنوب‌شرق"]: return f"از سمت {direction} (منشأ: بیابان‌های عربستان)"
        elif direction == "غرب": return f"از سمت {direction} (منشأ: صحرای عربستان)"
    elif city_name in ["چابهار", "جاسک", "کنارک"]:
        if direction in ["جنوب", "جنوب‌غرب"]: return f"از سمت {direction} (منشأ: دریای عمان)"
        elif direction in ["شمال", "شمال‌شرق"]: return f"از سمت {direction} (منشأ: پاکستان)"
        elif direction == "شرق": return f"از سمت {direction} (منشأ: اقیانوس هند)"
    elif city_name in ["زابل (سیستان)", "زاهدان", "مکران"]:
        if direction in ["شمال", "شمال‌غرب", "غرب"]: return f"از سمت {direction} (منشأ: کویرهای مرکزی ایران)"
        elif direction in ["جنوب", "جنوب‌شرق", "شرق"]: return f"از سمت {direction} (منشأ: بیابان‌های افغانستان و پاکستان)"
    elif city_name == "تهران":
        if direction in ["غرب", "جنوب‌غرب"]: return f"از سمت {direction} (منشأ: کویر مرکزی و دشت‌های غربی)"
    return f"از سمت {direction}"

# --- منوها ---
def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌤️ آب و هوای شهرها", callback_data="menu_weather")],
        [InlineKeyboardButton("🚨 وضعیت طوفان", callback_data="menu_storm_cities")],
        [InlineKeyboardButton("🌫️ وضعیت گرد و خاک", callback_data="menu_dust_cities")],
        [InlineKeyboardButton("🏭 آلودگی هوا", callback_data="menu_air_cities")],
        [InlineKeyboardButton("🏖️ مناطق ساحلی", callback_data="menu_coastal")],
        [InlineKeyboardButton("📚 جستجوی مقاله", callback_data="menu_search_paper")],
        [InlineKeyboardButton("🌀 طوفان‌های حاره‌ای", callback_data="menu_cyclone")],
        [InlineKeyboardButton("🔬 اقیانوس‌شناسی (علمی)", callback_data="ocean_main")],
    ])

def get_back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]])

def get_region_menu(prefix):
    kb = [[InlineKeyboardButton(region, callback_data=f"{prefix}_region_{region}")] for region in INLAND_REGIONS.keys()]
    kb.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")])
    return InlineKeyboardMarkup(kb)

def get_city_menu(prefix, city_dict):
    kb = []
    cities = list(city_dict.keys())
    for i in range(0, len(cities), 2):
        row = [InlineKeyboardButton(cities[i], callback_data=f"{prefix}_{cities[i]}")]
        if i + 1 < len(cities): row.append(InlineKeyboardButton(cities[i+1], callback_data=f"{prefix}_{cities[i+1]}"))
        kb.append(row)
    kb.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")])
    return InlineKeyboardMarkup(kb)

def get_keyword_menu():
    kb = []
    for i in range(0, len(KEYWORD_TOPICS), 2):
        row = [InlineKeyboardButton(KEYWORD_TOPICS[i][0], callback_data=f"kw_{KEYWORD_TOPICS[i][1]}")]
        if i + 1 < len(KEYWORD_TOPICS): row.append(InlineKeyboardButton(KEYWORD_TOPICS[i+1][0], callback_data=f"kw_{KEYWORD_TOPICS[i+1][1]}"))
        kb.append(row)
    kb.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")])
    return InlineKeyboardMarkup(kb)

def get_coastal_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌊 خلیج فارس", callback_data="coastal_gulf")],
        [InlineKeyboardButton("🌊 دریای عمان", callback_data="coastal_oman")],
        [InlineKeyboardButton("🌊 دریای خزر", callback_data="coastal_caspian")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")],
    ])

# --- منوهای اقیانوس‌شناسی ---
def get_ocean_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌊 فیزیک و شیمی دریا", callback_data="ocean_phys_chem")],
        [InlineKeyboardButton("🐟 زیست‌شناسی و آلودگی", callback_data="ocean_bio_poll")],
        [InlineKeyboardButton("📚 منابع علمی", callback_data="ocean_resources")],
        [InlineKeyboardButton("⚙️ مهندسی دریا", callback_data="ocean_engineering")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")],
    ])

def get_ocean_phys_chem_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌡️ دمای سطح آب و شوری", callback_data="pc_sst_sal")],
        [InlineKeyboardButton("⚖️ اکسیژن و pH", callback_data="pc_do_ph")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="ocean_main")],
    ])

def get_ocean_bio_poll_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 کلروفیل و فیتوپلانکتون", callback_data="bp_chl")],
        [InlineKeyboardButton("🧴 میکروپلاستیک و کربن آبی", callback_data="bp_micro_blue")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="ocean_main")],
    ])

def get_ocean_resources_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📰 اخبار علمی روز", callback_data="res_news")],
        [InlineKeyboardButton("📄 مقالات علمی", callback_data="res_papers")],
        [InlineKeyboardButton("📖 کتاب‌های اقیانوس‌شناسی", callback_data="res_books")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="ocean_main")],
    ])

def get_ocean_engineering_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚓ سازه‌های دریایی", callback_data="eng_structures")],
        [InlineKeyboardButton("📡 سنجش از دور", callback_data="eng_remote")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="ocean_main")],
    ])

def get_ocean_papers_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("اقیانوس‌شناسی", callback_data="op_oceanography")],
        [InlineKeyboardButton("میکروپلاستیک", callback_data="op_microplastic")],
        [InlineKeyboardButton("کربن آبی", callback_data="op_blue_carbon")],
        [InlineKeyboardButton("مرجان‌ها", callback_data="op_coral_reef")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="ocean_resources")],
    ])

# --- هندلرها ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 **به داشبورد اقلیم خوش آمدید.**", reply_markup=get_main_menu(), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    try:
        if data == "menu_main":
            await query.edit_message_text("منوی اصلی:", reply_markup=get_main_menu())

        # --- اقیانوس‌شناسی ---
        elif data.startswith("ocean_") or data.startswith("pc_") or data.startswith("bp_") or data.startswith("res_") or data.startswith("eng_") or data.startswith("op_"):
            if data == "ocean_main": await query.edit_message_text("🔬 **بخش اقیانوس‌شناسی (علمی)**\n\nلطفاً یک گزینه را انتخاب کنید:", reply_markup=get_ocean_main_menu(), parse_mode='Markdown')
            elif data == "ocean_phys_chem": await query.edit_message_text("🌊 **فیزیک و شیمی دریا**\n\nلطفاً یک موضوع را انتخاب کنید:", reply_markup=get_ocean_phys_chem_menu())
            elif data == "pc_sst_sal": await query.edit_message_text("🌡️ **دمای سطح آب و شوری**\n\n(در حال توسعه)", reply_markup=get_ocean_phys_chem_menu())
            elif data == "pc_do_ph": await query.edit_message_text("⚖️ **اکسیژن و pH**\n\n(در حال توسعه)", reply_markup=get_ocean_phys_chem_menu())
            elif data == "ocean_bio_poll": await query.edit_message_text("🐟 **زیست‌شناسی و آلودگی**\n\nلطفاً یک موضوع را انتخاب کنید:", reply_markup=get_ocean_bio_poll_menu())
            elif data == "bp_chl": await query.edit_message_text("🟢 **کلروفیل و فیتوپلانکتون**\n\n(در حال توسعه)", reply_markup=get_ocean_bio_poll_menu())
            elif data == "bp_micro_blue": await query.edit_message_text("🧴 **میکروپلاستیک و کربن آبی**\n\n(در حال توسعه)", reply_markup=get_ocean_bio_poll_menu())
            elif data == "ocean_resources": await query.edit_message_text("📚 **منابع علمی**\n\nلطفاً یک گزینه را انتخاب کنید:", reply_markup=get_ocean_resources_menu())
            elif data == "res_news":
                await query.edit_message_text("⏳ در حال دریافت اخبار...")
                r = requests.get("https://www.sciencedaily.com/rss/earth_climate/oceanography.xml", timeout=15)
                root = ET.fromstring(r.content)
                msg = "📰 **اخبار علمی روز**\n\n"
                for item in root.findall('.//item')[:3]:
                    msg += f"🔹 {item.find('title').text}\n   🔗 [لینک]({item.find('link').text})\n\n"
                await query.edit_message_text(msg, reply_markup=get_ocean_resources_menu(), disable_web_page_preview=True)
            elif data == "res_papers": await query.edit_message_text("📄 **مقالات علمی**\n\nلطفاً موضوع را انتخاب کنید:", reply_markup=get_ocean_papers_menu())
            elif data == "res_books": await query.edit_message_text("📖 **کتاب‌ها**\n\n(در حال توسعه)", reply_markup=get_ocean_resources_menu())
            elif data.startswith("op_"):
                kw = data.replace("op_", "")
                res = search_openalex(kw, 1)
                if res:
                    msg = f"📚 **نتایج:**\n\n"
                    for i, r in enumerate(res, 1): msg += f"{i}. **{r['title']}**\n   👤 {r['author']} | 📅 {r['year']}\n   🔗 [لینک]({r['link']})\n\n"
                    await query.edit_message_text(msg, reply_markup=get_ocean_resources_menu())
                else: await query.edit_message_text("نتیجه‌ای یافت نشد.", reply_markup=get_ocean_resources_menu())
            elif data == "ocean_engineering": await query.edit_message_text("⚙️ **مهندسی دریا**\n\nلطفاً یک موضوع را انتخاب کنید:", reply_markup=get_ocean_engineering_menu())
            elif data == "eng_structures": await query.edit_message_text("⚓ **سازه‌های دریایی**\n\n(در حال توسعه)", reply_markup=get_ocean_engineering_menu())
            elif data == "eng_remote": await query.edit_message_text("📡 **سنجش از دور**\n\n(در حال توسعه)", reply_markup=get_ocean_engineering_menu())

        # --- مناطق ساحلی ---
        elif data == "menu_coastal": await query.edit_message_text("🏖️ **بخش مناطق ساحلی**\n\nلطفاً یک گزینه را انتخاب کنید:", reply_markup=get_coastal_menu())
        elif data == "coastal_gulf": await query.edit_message_text("📍 شهر در خلیج فارس:", reply_markup=get_city_menu("coastal_gulf", {**PERSIAN_GULF_CITIES, **PERSIAN_GULF_ISLANDS}))
        elif data.startswith("coastal_gulf_"):
            city = data.replace("coastal_gulf_", "")
            # (کد ارسال گزارش دریایی مشابه بله در اینجا قرار می‌گیرد)
            await query.edit_message_text(f"🌊 **{city}**\n\n(داده‌ها به زودی)", reply_markup=get_coastal_menu())
        elif data == "coastal_oman": await query.edit_message_text("📍 شهر در دریای عمان:", reply_markup=get_city_menu("coastal_oman", OMAN_SEA_CITIES))
        elif data.startswith("coastal_oman_"):
            city = data.replace("coastal_oman_", "")
            await query.edit_message_text(f"🌊 **{city}**\n\n(داده‌ها به زودی)", reply_markup=get_coastal_menu())
        elif data == "coastal_caspian": await query.edit_message_text("📍 شهر در دریای خزر:", reply_markup=get_city_menu("coastal_caspian", CASPIAN_CITIES))
        elif data.startswith("coastal_caspian_"):
            city = data.replace("coastal_caspian_", "")
            await query.edit_message_text(f"🌊 **{city}**\n\n(داده‌ها به زودی)", reply_markup=get_coastal_menu())

        # --- بخش‌های منطقه‌ای ---
        elif data == "menu_weather": await query.edit_message_text("📍 منطقه مورد نظر را انتخاب کنید:", reply_markup=get_region_menu("weather"))
        elif data.startswith("weather_region_"):
            region = data.replace("weather_region_", "")
            if region in INLAND_REGIONS: await query.edit_message_text(f"📍 شهر در منطقه {region}:", reply_markup=get_city_menu("w", INLAND_REGIONS[region]))
        elif data.startswith("w_"):
            city = data.replace("w_", "")
            if city in ALL_CITIES:
                res = get_hourly_weather(*ALL_CITIES[city])
                if res and "hourly" in res:
                    h = res["hourly"]; msg = f"🌤️ **آب‌وهوای {city} (ساعتی):**\n\n"
                    for i in range(0, 48, 2): 
                        if i < len(h['time']):
                            t = h['temperature_2m'][i]; rain = h['precipitation'][i]
                            w = "آفتابی" if h['weather_code'][i] == 0 else "ابری" if h['weather_code'][i] in [1,2,3] else "بارانی" if h['weather_code'][i] > 50 else "برفی"
                            msg += f"🕐 {h['time'][i][11:16]} | 🌡️ {round(t, 1)}° | {w} | 🌧️ {round(rain, 1)} mm\n"
                    await query.edit_message_text(msg, reply_markup=get_back_button())

        elif data == "menu_storm_cities": await query.edit_message_text("📍 منطقه مورد نظر را انتخاب کنید:", reply_markup=get_region_menu("storm"))
        elif data.startswith("storm_region_"):
            region = data.replace("storm_region_", "")
            if region in INLAND_REGIONS: await query.edit_message_text(f"📍 شهر در منطقه {region}:", reply_markup=get_city_menu("storm", INLAND_REGIONS[region]))
        elif data.startswith("storm_"):
            city = data.replace("storm_", "")
            if city in ALL_CITIES:
                res = get_hourly_weather(*ALL_CITIES[city])
                if res and "hourly" in res:
                    h = res["hourly"]; max_wind = max(h['wind_speed_10m'][:24]) if h.get('wind_speed_10m') else 0
                    analysis = "🚨 خطرناک" if max_wind > 60 else "⚠️ هشدار" if max_wind > 40 else "🌬️ نسیم" if max_wind > 20 else "✅ آرام"
                    msg = f"🚨 **طوفان {city}:**\n\n💨 حداکثر باد (۲۴h): {round(max_wind, 1)} km/h\n📌 {analysis}"
                    await query.edit_message_text(msg, reply_markup=get_back_button())

        elif data == "menu_dust_cities": await query.edit_message_text("📍 منطقه مورد نظر را انتخاب کنید:", reply_markup=get_region_menu("dust"))
        elif data.startswith("dust_region_"):
            region = data.replace("dust_region_", "")
            if region in INLAND_REGIONS: await query.edit_message_text(f"📍 شهر در منطقه {region}:", reply_markup=get_city_menu("dust", INLAND_REGIONS[region]))
        elif data.startswith("dust_"):
            city = data.replace("dust_", "")
            if city in ALL_CITIES:
                res = get_dust_data(*ALL_CITIES[city])
                if res and "hourly" in res:
                    dust = res["hourly"]["dust"][0]; pm10 = res["hourly"]["pm10"][0]
                    analysis = "🔴 هشدار" if dust and dust > 50 else "🟡 متوسط" if dust and dust > 20 else "🟢 پاک"
                    msg = f"🌫️ **گرد و خاک {city}:**\n\n🌪️ Dust: {round(dust, 1) if dust else 'نامشخص'} | 💨 PM10: {round(pm10, 1) if pm10 else 'نامشخص'}\n📌 {analysis}"
                    await query.edit_message_text(msg, reply_markup=get_back_button())

        elif data == "menu_air_cities": await query.edit_message_text("📍 منطقه مورد نظر را انتخاب کنید:", reply_markup=get_region_menu("air"))
        elif data.startswith("air_region_"):
            region = data.replace("air_region_", "")
            if region in INLAND_REGIONS: await query.edit_message_text(f"📍 شهر در منطقه {region}:", reply_markup=get_city_menu("air", INLAND_REGIONS[region]))
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
                    await query.edit_message_text(msg, reply_markup=get_back_button())

        elif data == "menu_search_paper": await query.edit_message_text("📚 موضوع مورد نظر را انتخاب کنید:", reply_markup=get_keyword_menu())
        elif data.startswith("kw_") and not data.startswith("kwmore_"):
            kw = data.replace("kw_", ""); await query.edit_message_text(f"⏳ در حال جستجو برای «{kw}»...")
            res = search_openalex(kw, 2020, 1)
            if res:
                msg = f"📚 **نتایج «{kw}»:**\n\n"
                for i, r in enumerate(res, 1): msg += f"{i}. **{r['title']}**\n   👤 {r['author']} | 📅 {r['year']}\n   🔗 [لینک]({r['link']})\n\n"
                kb = [[InlineKeyboardButton("📄 بیشتر", callback_data=f"kwmore_{kw}_2")], [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_search_paper")]]
                await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown', disable_web_page_preview=True)
        elif data.startswith("kwmore_"):
            parts = data.replace("kwmore_", "").split("_"); kw, page = parts[0], int(parts[1])
            await query.edit_message_text(f"⏳ در حال جستجو...")
            res = search_openalex(kw, 2020, page)
            if res:
                msg = f"📚 **نتایج «{kw}»:**\n\n"
                for i, r in enumerate(res, 1): msg += f"{i}. **{r['title']}**\n   👤 {r['author']} | 📅 {r['year']}\n   🔗 [لینک]({r['link']})\n\n"
                kb = [[InlineKeyboardButton("📄 بیشتر", callback_data=f"kwmore_{kw}_{page+1}")], [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_search_paper")]]
                await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown', disable_web_page_preview=True)

        elif data == "menu_cyclone": await query.edit_message_text("🌀 **طوفان‌های حاره‌ای:**\n\nدر حال حاضر طوفان فعالی گزارش نشده است.", reply_markup=get_back_button())

    except Exception as e:
        print(f"Error: {e}")
        if "Message is not modified" not in str(e):
            try: await query.message.reply_text("❌ خطایی رخ داد.", reply_markup=get_main_menu())
            except: pass

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("=" * 60 + "\nربات تلگرام روشن شد...\n" + "=" * 60)
    app.run_polling()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    main()