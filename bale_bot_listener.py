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

load_dotenv()

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

BALE_TOKEN = os.getenv("BALE_TOKEN")

# ==========================================
# ۱. دیکشنری‌های تفکیک‌شده (بدون تغییر)
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
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌤️ آب و هوای شهرها", callback_data="menu_weather")],
        [InlineKeyboardButton(text="🚨 وضعیت طوفان", callback_data="menu_storm_cities")],
        [InlineKeyboardButton(text="🌫️ وضعیت گرد و خاک", callback_data="menu_dust_cities")],
        [InlineKeyboardButton(text="🏭 آلودگی هوا", callback_data="menu_air_cities")],
        [InlineKeyboardButton(text="🏖️ مناطق ساحلی", callback_data="menu_coastal")],
        [InlineKeyboardButton(text="📚 جستجوی مقاله", callback_data="menu_search_paper")],
        [InlineKeyboardButton(text="🌀 طوفان‌های حاره‌ای", callback_data="menu_cyclone")],
        [InlineKeyboardButton(text="🔬 اقیانوس‌شناسی (علمی)", callback_data="ocean_main")], # دکمه جدید
    ])

def get_back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
    ])

def get_region_menu(prefix):
    kb = [[InlineKeyboardButton(text=region, callback_data=f"{prefix}_region_{region}")] for region in INLAND_REGIONS.keys()]
    kb.append([InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_city_menu(prefix, city_dict):
    kb = []
    cities = list(city_dict.keys())
    for i in range(0, len(cities), 2):
        row = [InlineKeyboardButton(text=cities[i], callback_data=f"{prefix}_{cities[i]}")]
        if i + 1 < len(cities): row.append(InlineKeyboardButton(text=cities[i+1], callback_data=f"{prefix}_{cities[i+1]}"))
        kb.append(row)
    kb.append([InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_keyword_menu():
    kb = []
    for i in range(0, len(KEYWORD_TOPICS), 2):
        row = [InlineKeyboardButton(text=KEYWORD_TOPICS[i][0], callback_data=f"kw_{KEYWORD_TOPICS[i][1]}")]
        if i + 1 < len(KEYWORD_TOPICS): row.append(InlineKeyboardButton(text=KEYWORD_TOPICS[i+1][0], callback_data=f"kw_{KEYWORD_TOPICS[i+1][1]}"))
        kb.append(row)
    kb.append([InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_coastal_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌊 خلیج فارس", callback_data="coastal_gulf")],
        [InlineKeyboardButton(text="🌊 دریای عمان", callback_data="coastal_oman")],
        [InlineKeyboardButton(text="🌊 دریای خزر", callback_data="coastal_caspian")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="menu_main")],
    ])

# ==========================================
# ۲. کدهای بخش اقیانوس‌شناسی (جدید - بدون تغییر در کدهای قبلی)
# ==========================================
def get_ocean_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌊 فیزیک و شیمی دریا", callback_data="ocean_phys_chem")],
        [InlineKeyboardButton(text="🐟 زیست‌شناسی و آلودگی", callback_data="ocean_bio_poll")],
        [InlineKeyboardButton(text="📚 منابع علمی", callback_data="ocean_resources")],
        [InlineKeyboardButton(text="⚙️ مهندسی دریا", callback_data="ocean_engineering")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="menu_main")],
    ])

def get_ocean_phys_chem_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌡️ دمای سطح آب و شوری", callback_data="pc_sst_sal")],
        [InlineKeyboardButton(text="⚖️ اکسیژن و pH", callback_data="pc_do_ph")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="ocean_main")],
    ])

def get_ocean_bio_poll_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 کلروفیل و فیتوپلانکتون", callback_data="bp_chl")],
        [InlineKeyboardButton(text="🧴 میکروپلاستیک و کربن آبی", callback_data="bp_micro_blue")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="ocean_main")],
    ])

def get_ocean_resources_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📰 اخبار علمی روز", callback_data="res_news")],
        [InlineKeyboardButton(text="📄 مقالات علمی", callback_data="res_papers")],
        [InlineKeyboardButton(text="📖 کتاب‌های اقیانوس‌شناسی", callback_data="res_books")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="ocean_main")],
    ])

def get_ocean_engineering_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚓ سازه‌های دریایی", callback_data="eng_structures")],
        [InlineKeyboardButton(text="📡 سنجش از دور", callback_data="eng_remote")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="ocean_main")],
    ])

def get_ocean_papers_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="اقیانوس‌شناسی", callback_data="op_oceanography")],
        [InlineKeyboardButton(text="میکروپلاستیک", callback_data="op_microplastic")],
        [InlineKeyboardButton(text="کربن آبی", callback_data="op_blue_carbon")],
        [InlineKeyboardButton(text="مرجان‌ها", callback_data="op_coral_reef")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="ocean_resources")],
    ])

# --- توابع دریافت داده برای بخش اقیانوس‌شناسی ---
def fetch_ocean_news():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get("https://www.sciencedaily.com/rss/earth_climate/oceanography.xml", headers=headers, timeout=15)
        r.raise_for_status()
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.content)
        items = root.findall('.//item')[:3]
        news = []
        for item in items:
            title = item.find('title')
            link = item.find('link')
            if title is not None and link is not None:
                news.append({"title": title.text, "link": link.text})
        return news
    except: return []

async def handle_ocean_callback(callback, data):
    try:
        if data == "ocean_main":
            await callback.message.edit_text("🔬 **بخش اقیانوس‌شناسی (علمی)**\n\nلطفاً یک گزینه را انتخاب کنید:", reply_markup=get_ocean_main_menu())
        
        elif data == "ocean_phys_chem":
            await callback.message.edit_text("🌊 **فیزیک و شیمی دریا**\n\nلطفاً یک موضوع را انتخاب کنید:", reply_markup=get_ocean_phys_chem_menu())
        elif data == "pc_sst_sal":
            await callback.message.edit_text("🌡️ **دمای سطح آب و شوری**\n\n(در حال توسعه)", reply_markup=get_ocean_phys_chem_menu())
        elif data == "pc_do_ph":
            await callback.message.edit_text("⚖️ **اکسیژن و pH**\n\n(در حال توسعه)", reply_markup=get_ocean_phys_chem_menu())

        elif data == "ocean_bio_poll":
            await callback.message.edit_text("🐟 **زیست‌شناسی و آلودگی**\n\nلطفاً یک موضوع را انتخاب کنید:", reply_markup=get_ocean_bio_poll_menu())
        elif data == "bp_chl":
            await callback.message.edit_text("🟢 **کلروفیل و فیتوپلانکتون**\n\n(در حال توسعه)", reply_markup=get_ocean_bio_poll_menu())
        elif data == "bp_micro_blue":
            await callback.message.edit_text("🧴 **میکروپلاستیک و کربن آبی**\n\n(در حال توسعه)", reply_markup=get_ocean_bio_poll_menu())

        elif data == "ocean_resources":
            await callback.message.edit_text("📚 **منابع علمی**\n\nلطفاً یک گزینه را انتخاب کنید:", reply_markup=get_ocean_resources_menu())
        elif data == "res_news":
            news = fetch_ocean_news()
            msg = "📰 **اخبار علمی روز**\n\n"
            if news:
                for n in news: msg += f"🔹 {n['title']}\n   🔗 [لینک]({n['link']})\n\n"
            else: msg += "خبری در دسترس نیست."
            await callback.message.edit_text(msg, reply_markup=get_ocean_resources_menu(), disable_web_page_preview=True)
        elif data == "res_papers":
            await callback.message.edit_text("📄 **مقالات علمی**\n\nلطفاً موضوع را انتخاب کنید:", reply_markup=get_ocean_papers_menu())
        elif data == "res_books":
            msg = "📖 **کتاب‌های اقیانوس‌شناسی**\n\n"
            books = ["کتاب: Climate Dynamics (Kerry H. Cook)", "کتاب: Oceanography (Tom Garrison)", "کتاب: Chemical Oceanography (Frank J. Millero)"]
            for b in books: msg += f"🔹 {b}\n"
            await callback.message.edit_text(msg, reply_markup=get_ocean_resources_menu())
        elif data.startswith("op_"):
            kw = data.replace("op_", ""); await callback.message.edit_text(f"⏳ در حال جستجو...")
            res = search_openalex(kw, 2020, 1)
            if res:
                msg = f"📚 **نتایج «{kw}»:**\n\n"
                for i, r in enumerate(res, 1): msg += f"{i}. **{r['title']}**\n   👤 {r['author']} | 📅 {r['year']}\n   🔗 [لینک]({r['link']})\n\n"
                await callback.message.edit_text(msg, reply_markup=get_ocean_resources_menu())
            else: await callback.message.edit_text("نتیجه‌ای یافت نشد.", reply_markup=get_ocean_resources_menu())

        elif data == "ocean_engineering":
            await callback.message.edit_text("⚙️ **مهندسی دریا**\n\nلطفاً یک موضوع را انتخاب کنید:", reply_markup=get_ocean_engineering_menu())
        elif data == "eng_structures":
            await callback.message.edit_text("⚓ **سازه‌های دریایی**\n\n(در حال توسعه)", reply_markup=get_ocean_engineering_menu())
        elif data == "eng_remote":
            await callback.message.edit_text("📡 **سنجش از دور**\n\n(در حال توسعه)", reply_markup=get_ocean_engineering_menu())
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            try: await callback.message.answer("❌ خطایی رخ داد.")
            except: pass

# ==========================================
# ۳. توابع اصلی (بدون تغییر)
# ==========================================
async def send_coastal_report(callback, city_name, lat, lon):
    try:
        await callback.message.edit_text(f"⏳ در حال دریافت داده‌های {city_name}...")
        marine_res = get_marine_data(lat, lon)
        weather_res = get_hourly_weather(lat, lon)
        
        msg = f"🏖️ **{city_name}** 🏖️\n\n"
        
        if marine_res and "hourly" in marine_res:
            h = marine_res["hourly"]
            def s_val(val, dec=1):
                try: return round(float(val), dec) if val is not None else "نامشخص"
                except: return "نامشخص"
            
            wave = s_val(h['wave_height'][0] if h.get('wave_height') else None, 2)
            wave_dir_raw = h['wave_direction'][0] if h.get('wave_direction') else None
            wave_dir_text = degree_to_direction(wave_dir_raw) if wave_dir_raw is not None else "نامشخص"
            w_per = s_val(h['wave_period'][0] if h.get('wave_period') else None)
            curr = s_val(h['ocean_current_velocity'][0] if h.get('ocean_current_velocity') else None)

            msg += f"📏 **موج:**\n   ارتفاع: {wave} متر\n   جهت: {wave_dir_text}\n   دوره: {w_per} ثانیه\n   جریان: {curr} کیلومتر بر ساعت\n"
        else:
            msg += "📏 **موج:** داده در دسترس نیست.\n"
            
        if weather_res and "hourly" in weather_res:
            h = weather_res["hourly"]
            def s_val(val, dec=1):
                try: return round(float(val), dec) if val is not None else "نامشخص"
                except: return "نامشخص"

            w_spd = s_val(h['wind_speed_10m'][0] if h.get('wind_speed_10m') else None)
            wind_dir_raw = h['wind_direction_10m'][0] if h.get('wind_direction_10m') else None
            
            if wind_dir_raw is not None:
                wind_analysis = get_wind_analysis(city_name, wind_dir_raw)
            else:
                wind_analysis = "نامشخص"
            
            msg += f"\n💨 **باد:**\n   سرعت: {w_spd} کیلومتر بر ساعت\n   جهت: {wind_analysis}\n"
        else:
            msg += "\n💨 **باد:** داده در دسترس نیست.\n"

        await callback.message.edit_text(msg, reply_markup=get_coastal_menu())
    except Exception as e:
        await callback.message.edit_text(f"❌ خطا در دریافت داده‌های {city_name}.", reply_markup=get_coastal_menu())
        print(f"Coastal Error {city_name}: {e}")

async def main():
    bot = Bot(token=BALE_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher()

    @dp.message()
    async def on_message(message: Message):
        await message.answer("👋 **به داشبورد اقلیم خوش آمدید.**", reply_markup=get_main_menu())

    @dp.callback_query()
    async def on_callback(callback: CallbackQuery):
        data = callback.data
        try:
            # --- منوی اصلی ---
            if data == "menu_main": await callback.message.edit_text("منوی اصلی:", reply_markup=get_main_menu())
            
            # --- اقیانوس‌شناسی (جدید) ---
            elif data.startswith("ocean_") or data.startswith("pc_") or data.startswith("bp_") or data.startswith("res_") or data.startswith("eng_") or data.startswith("op_"):
                await handle_ocean_callback(callback, data)

            # --- مناطق ساحلی ---
            elif data == "menu_coastal":
                await callback.message.edit_text("🏖️ **بخش مناطق ساحلی**\n\nلطفاً یک گزینه را انتخاب کنید:", reply_markup=get_coastal_menu())
            elif data == "coastal_gulf":
                await callback.message.edit_text("📍 لطفاً یک منطقه در خلیج فارس را انتخاب کنید:", reply_markup=get_city_menu("coastal_gulf", {**PERSIAN_GULF_CITIES, **PERSIAN_GULF_ISLANDS}))
            elif data.startswith("coastal_gulf_"):
                city = data.replace("coastal_gulf_", "")
                all_gulf = {**PERSIAN_GULF_CITIES, **PERSIAN_GULF_ISLANDS}
                if city in all_gulf: await send_coastal_report(callback, city, *all_gulf[city])
            elif data == "coastal_oman":
                await callback.message.edit_text("📍 لطفاً یک منطقه در دریای عمان را انتخاب کنید:", reply_markup=get_city_menu("coastal_oman", OMAN_SEA_CITIES))
            elif data.startswith("coastal_oman_"):
                city = data.replace("coastal_oman_", "")
                if city in OMAN_SEA_CITIES: await send_coastal_report(callback, city, *OMAN_SEA_CITIES[city])
            elif data == "coastal_caspian":
                await callback.message.edit_text("📍 لطفاً یک منطقه در دریای خزر را انتخاب کنید:", reply_markup=get_city_menu("coastal_caspian", CASPIAN_CITIES))
            elif data.startswith("coastal_caspian_"):
                city = data.replace("coastal_caspian_", "")
                if city in CASPIAN_CITIES: await send_coastal_report(callback, city, *CASPIAN_CITIES[city])

            # --- بخش‌های منطقه‌ای ---
            elif data == "menu_weather": await callback.message.edit_text("📍 منطقه مورد نظر را انتخاب کنید:", reply_markup=get_region_menu("weather"))
            elif data.startswith("weather_region_"):
                region = data.replace("weather_region_", "")
                if region in INLAND_REGIONS: await callback.message.edit_text(f"📍 شهر در منطقه {region}:", reply_markup=get_city_menu("w", INLAND_REGIONS[region]))
            elif data.startswith("w_"):
                city = data.replace("w_", "")
                if city in ALL_CITIES:
                    res = get_hourly_weather(*ALL_CITIES[city])
                    if res and "hourly" in res:
                        h = res["hourly"]; msg = f"🌤️ **آب‌وهوای {city} (ساعتی - ۲ روز آینده):**\n\n"
                        for i in range(0, 48, 2): 
                            if i < len(h['time']):
                                t = h['temperature_2m'][i]; rain = h['precipitation'][i]
                                w = "آفتابی" if h['weather_code'][i] == 0 else "ابری" if h['weather_code'][i] in [1,2,3] else "بارانی" if h['weather_code'][i] > 50 else "برفی"
                                msg += f"🕐 {h['time'][i][11:16]} | 🌡️ {round(t, 1)} درجه | {w} | 🌧️ {round(rain, 1)} میلی‌متر\n"
                        await callback.message.edit_text(msg, reply_markup=get_back_button())

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
                        msg = f"🚨 **طوفان {city}:**\n\n💨 حداکثر باد (۲۴ ساعت آینده): {round(max_wind, 1)} کیلومتر بر ساعت\n📌 {analysis}"
                        await callback.message.edit_text(msg, reply_markup=get_back_button())

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
                        msg = f"🌫️ **گرد و خاک {city}:**\n\n🌪️ گرد و خاک: {round(dust, 1) if dust else 'نامشخص'} | 💨 ذرات: {round(pm10, 1) if pm10 else 'نامشخص'}\n📌 {analysis}"
                        await callback.message.edit_text(msg, reply_markup=get_back_button())

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
                        msg = f"🏭 **آلودگی هوای {city}:**\n\n🔹 ذرات معلق: {round(pm25, 1) if pm25 else 'نامشخص'} میکروگرم بر متر مکعب\n📊 وضعیت: {status}"
                        await callback.message.edit_text(msg, reply_markup=get_back_button())

            elif data == "menu_search_paper": await callback.message.edit_text("📚 موضوع مورد نظر را انتخاب کنید:", reply_markup=get_keyword_menu())
            elif data.startswith("kw_") and not data.startswith("kwmore_"):
                kw = data.replace("kw_", ""); await callback.message.edit_text(f"⏳ در حال جستجو برای «{kw}»...")
                res = search_openalex(kw, 2020, 1)
                if res:
                    msg = f"📚 **نتایج «{kw}»:**\n\n"
                    for i, r in enumerate(res, 1): msg += f"{i}. **{r['title']}**\n   👤 {r['author']} | 📅 {r['year']}\n   🔗 [لینک]({r['link']})\n\n"
                    kb = [[InlineKeyboardButton(text="📄 بیشتر", callback_data=f"kwmore_{kw}_2")], [InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu_search_paper")]]
                    await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            elif data.startswith("kwmore_"):
                parts = data.replace("kwmore_", "").split("_"); kw, page = parts[0], int(parts[1])
                await callback.message.edit_text(f"⏳ در حال جستجو...")
                res = search_openalex(kw, 2020, page)
                if res:
                    msg = f"📚 **نتایج «{kw}»:**\n\n"
                    for i, r in enumerate(res, 1): msg += f"{i}. **{r['title']}**\n   👤 {r['author']} | 📅 {r['year']}\n   🔗 [لینک]({r['link']})\n\n"
                    kb = [[InlineKeyboardButton(text="📄 بیشتر", callback_data=f"kwmore_{kw}_{page+1}")], [InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu_search_paper")]]
                    await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

            elif data == "menu_cyclone": await callback.message.edit_text("🌀 **طوفان‌های حاره‌ای:**\n\nدر حال حاضر طوفان فعالی گزارش نشده است.\n🔗 https://www.rsmcnewdelhi.imd.gov.in/", reply_markup=get_back_button())

        except Exception as e:
            print(f"Error: {e}")
            if "message is not modified" not in str(e).lower():
                try: await callback.message.answer("❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.", reply_markup=get_main_menu())
                except: pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())