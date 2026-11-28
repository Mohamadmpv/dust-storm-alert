import asyncio
import logging
import sys
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from baleio import Bot, Dispatcher
from baleio.client.default import DefaultBotProperties
from baleio.enums import ParseMode
from baleio.types import Message, CallbackQuery
from baleio.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

BALE_TOKEN = os.getenv("BALE_TOKEN")

# --- توابع کمکی ---
def get_back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اقیانوس‌شناسی", callback_data="ocean_main")]
    ])

def search_openalex(keyword, page=1, year_from=2020):
    url = "https://api.openalex.org/works"
    filter_str = f"from_publication_date:{year_from}-01-01,title_and_abstract.search:{keyword}"
    params = {"filter": filter_str, "sort": "relevance_score:desc", "per_page": 5, "page": page}
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        return [{"title": w.get("title", "بدون عنوان"), "year": w.get("publication_year", "نامشخص"), "link": w.get("doi") or w.get("id", ""), "author": w.get("authorships", [{}])[0].get("author", {}).get("display_name", "نامشخص")} for w in data.get("results", [])]
    except Exception as e:
        print(f"OpenAlex Error: {e}")
        return []

def fetch_rss_news(source_url, max_items=3):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(source_url, headers=headers, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = root.findall('.//item')[:max_items]
        news = []
        for item in items:
            title = item.find('title')
            link = item.find('link')
            pub_date = item.find('pubDate')
            date_str = ""
            if pub_date is not None and pub_date.text:
                try:
                    dt = datetime.strptime(pub_date.text[:16], "%a, %d %b %Y")
                    date_str = dt.strftime("%Y/%m/%d")
                except: pass
            if title is not None and link is not None:
                news.append({"title": title.text, "link": link.text, "date": date_str})
        return news
    except Exception as e:
        print(f"RSS Error: {e}")
        return []

# --- منوهای اصلی ---
def get_ocean_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌊 فیزیک و شیمی دریا", callback_data="ocean_phys_chem")],
        [InlineKeyboardButton(text="🐟 زیست‌شناسی و آلودگی", callback_data="ocean_bio_poll")],
        [InlineKeyboardButton(text="📚 منابع علمی", callback_data="ocean_resources")],
        [InlineKeyboardButton(text="⚙️ مهندسی دریا", callback_data="ocean_engineering")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main_bot")],
    ])

def get_phys_chem_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌡️ دمای سطح آب و شوری", callback_data="pc_sst_sal")],
        [InlineKeyboardButton(text="⚖️ اکسیژن و pH", callback_data="pc_do_ph")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="ocean_main")],
    ])

def get_bio_poll_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 کلروفیل و فیتوپلانکتون", callback_data="bp_chl")],
        [InlineKeyboardButton(text="🧴 میکروپلاستیک و کربن آبی", callback_data="bp_micro_blue")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="ocean_main")],
    ])

def get_resources_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📰 اخبار علمی روز", callback_data="res_news")],
        [InlineKeyboardButton(text="📄 مقالات علمی", callback_data="res_papers")],
        [InlineKeyboardButton(text="📖 کتاب‌های اقیانوس‌شناسی", callback_data="res_books")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="ocean_main")],
    ])

def get_engineering_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚓ سازه‌های دریایی", callback_data="eng_structures")],
        [InlineKeyboardButton(text="📡 سنجش از دور", callback_data="eng_remote")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="ocean_main")],
    ])

# --- منوی مقالات علمی (با موضوعات جدید) ---
def get_ocean_papers_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="اقیانوس‌شناسی عمومی", callback_data="op_oceanography")],
        [InlineKeyboardButton(text="میکروپلاستیک", callback_data="op_microplastic")],
        [InlineKeyboardButton(text="کربن آبی", callback_data="op_blue_carbon")],
        [InlineKeyboardButton(text="مرجان‌ها", callback_data="op_coral_reef")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="ocean_resources")],
    ])

async def main():
    bot = Bot(token=BALE_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher()

    @dp.message()
    async def on_message(message: Message):
        await message.answer("🔬 **به بخش علمی اقیانوس‌شناسی خوش آمدید.**", reply_markup=get_ocean_main_menu())

    @dp.callback_query()
    async def on_callback(callback: CallbackQuery):
        data = callback.data
        try:
            if data == "ocean_main":
                await callback.message.edit_text("🔬 **بخش اقیانوس‌شناسی (علمی)**\n\nلطفاً یک گزینه را انتخاب کنید:", reply_markup=get_ocean_main_menu())
            
            # --- فیزیک و شیمی ---
            elif data == "ocean_phys_chem":
                await callback.message.edit_text("🌊 **فیزیک و شیمی دریا**\n\nلطفاً یک موضوع را انتخاب کنید:", reply_markup=get_phys_chem_menu())
            elif data == "pc_sst_sal":
                msg = "🌡️ **دمای سطح آب و شوری (SST & Salinity)**\n\n"
                msg += "🔹 **دمای سطح آب:** در خلیج فارس و دریای عمان در تابستان به ۳۲-۳۶ درجه سانتی‌گراد و در زمستان به ۲۰-۲۴ درجه می‌رسد. در دریای خزر این دما پایین‌تر است.\n\n"
                msg += "🔹 **شوری:** خلیج فارس به دلیل تبخیر بالا، یکی از شورترین پهنه‌های آبی جهان است (۳۸-۴۰ psu). شوری خزر حدود ۱۲-۱۴ psu و عمان نزدیک به اقیانوس هند (۳۵-۳۷ psu) است.\n\n"
                msg += "📌 *برای دریافت داده‌های لحظه‌ای، از دیتاست‌های Copernicus Marine استفاده می‌شود.*"
                await callback.message.edit_text(msg, reply_markup=get_phys_chem_menu())
            elif data == "pc_do_ph":
                msg = "⚖️ **اکسیژن محلول (DO) و pH**\n\n"
                msg += "🔹 **اکسیژن محلول:** در سطح آب خلیج فارس حدود ۵-۷ میلی‌گرم بر لیتر است. در مناطق با شکوفایی جلبکی، این مقدار کاهش یافته و باعث ایجاد «مناطق مرده» (Hypoxia) می‌شود.\n\n"
                msg += "🔹 **pH:** آب دریاهای ایران قلیایی است (حدود ۸.۰ تا ۸.۲). افزایش CO2 اتمسفری باعث اسیدی شدن تدریجی (Ocean Acidification) و تهدید مرجان‌ها می‌شود."
                await callback.message.edit_text(msg, reply_markup=get_phys_chem_menu())

            # --- زیست‌شناسی و آلودگی ---
            elif data == "ocean_bio_poll":
                await callback.message.edit_text("🐟 **زیست‌شناسی و آلودگی**\n\nلطفاً یک موضوع را انتخاب کنید:", reply_markup=get_bio_poll_menu())
            elif data == "bp_chl":
                msg = "🟢 **کلروفیل و فیتوپلانکتون**\n\n"
                msg += "کلروفیل-a شاخص اصلی زیست‌توده فیتوپلانکتون‌هاست. در خلیج فارس، شکوفایی فیتوپلانکتون‌ها معمولاً در زمستان و اوایل بهار (به دلیل بادهای شمالی و اختلاط آب) رخ می‌دهد. این موجودات پایه زنجیره غذایی دریایی هستند و نقش کلیدی در جذب کربن (کربن آبی) دارند."
                await callback.message.edit_text(msg, reply_markup=get_bio_poll_menu())
            elif data == "bp_micro_blue":
                msg = "🧴 **میکروپلاستیک‌ها و کربن آبی**\n\n"
                msg += "🔹 **میکروپلاستیک:** ذرات پلاستیکی کمتر از ۵ میلی‌متر که تهدیدی جدی برای آبزیان و انسان هستند. خلیج فارس به دلیل ترافیک بالای کشتیرانی و صنایع، در معرض آلودگی میکروپلاستیک است.\n\n"
                msg += "🔹 **کربن آبی (Blue Carbon):** به کربنی گفته می‌شود که توسط اکوسیستم‌های دریایی (مانند جنگل‌های حرا، علف‌های دریایی و باتلاق‌های شور) جذب و ذخیره می‌شود. جنگل‌های حرای خلیج فارس نقش مهمی در این زمینه دارند."
                await callback.message.edit_text(msg, reply_markup=get_bio_poll_menu())

            # --- منابع علمی ---
            elif data == "ocean_resources":
                await callback.message.edit_text("📚 **منابع علمی**\n\nلطفاً یک گزینه را انتخاب کنید:", reply_markup=get_resources_menu())
            
            elif data == "res_news":
                await callback.message.edit_text("⏳ در حال دریافت اخبار علمی روز...")
                news1 = fetch_rss_news("https://www.sciencedaily.com/rss/earth_climate/oceanography.xml", 3)
                news2 = fetch_rss_news("https://www.sciencedaily.com/rss/plants_animals/marine_biology.xml", 2)
                all_news = news1 + news2
                msg = "📰 **اخبار علمی روز (اقیانوس‌شناسی و زیست‌شناسی دریایی)**\n\n"
                if all_news:
                    for n in all_news:
                        date_str = f" ({n['date']})" if n['date'] else ""
                        msg += f"🔹 {n['title']}{date_str}\n   🔗 [لینک]({n['link']})\n\n"
                else:
                    msg += "⚠️ خبر جدیدی در دسترس نیست."
                await callback.message.edit_text(msg, reply_markup=get_resources_menu(), disable_web_page_preview=True)
            
            elif data == "res_papers":
                await callback.message.edit_text("📄 **مقالات علمی (از سال ۲۰۲۰ به بعد)**\n\nلطفاً موضوع مورد نظر را انتخاب کنید:", reply_markup=get_ocean_papers_menu())
            
            elif data.startswith("op_"):
                kw = data.replace("op_", "")
                await callback.message.edit_text(f"⏳ در حال جستجو برای «{kw}» (از ۲۰۲۰ به بعد)...")
                res = search_openalex(kw, 1, 2020)
                if res:
                    msg = f"📚 **نتایج «{kw}» (از ۲۰۲۰ به بعد):**\n\n"
                    for i, r in enumerate(res, 1):
                        msg += f"{i}. **{r['title']}**\n   👤 {r['author']} | 📅 {r['year']}\n   🔗 [لینک]({r['link']})\n\n"
                    await callback.message.edit_text(msg, reply_markup=get_resources_menu(), disable_web_page_preview=True)
                else:
                    await callback.message.edit_text("⚠️ مقاله‌ای با این موضوع از سال ۲۰۲۰ به بعد یافت نشد.", reply_markup=get_resources_menu())

            elif data == "res_books":
                msg = "📖 **کتاب‌های مرجع اقیانوس‌شناسی**\n\n"
                msg += "🔹 **Oceanography: An Invitation to Marine Science** (Tom Garrison) - کتابی عالی برای شروع.\n"
                msg += "🔹 **Chemical Oceanography** (Frank J. Millero) - مرجع شیمی آب دریا.\n"
                msg += "🔹 **Climate Dynamics** (Kerry H. Cook) - برای درک فیزیک اقلیم و اقیانوس‌ها.\n\n"
                msg += "📌 *این کتاب‌ها از طریق سایت‌های ناشران بین‌المللی یا کتابخانه‌های دانشگاهی قابل تهیه هستند.*"
                await callback.message.edit_text(msg, reply_markup=get_resources_menu())

            # --- مهندسی دریا ---
            elif data == "ocean_engineering":
                await callback.message.edit_text("⚙️ **مهندسی دریا**\n\nلطفاً یک موضوع را انتخاب کنید:", reply_markup=get_engineering_menu())
            elif data == "eng_structures":
                msg = "⚓ **سازه‌های دریایی**\n\n"
                msg += "طراحی سکوهای نفتی، اسکله‌ها و آب‌شیرین‌کن‌ها نیازمند داده‌های دقیق هیدرودینامیکی (ارتفاع موج، سرعت جریان و باد) است. برای طراحی این سازه‌ها از استانداردهای بین‌المللی مانند API و ISO استفاده می‌شود."
                await callback.message.edit_text(msg, reply_markup=get_engineering_menu())
            elif data == "eng_remote":
                msg = "📡 **سنجش از دور دریایی**\n\n"
                msg += "برای پایش پهنه‌های آبی وسیع، از ماهواره‌ها استفاده می‌شود. ماهواره‌های Sentinel-3 (سازمان فضایی اروپا) و MODIS (ناسا) داده‌های ارزشمندی از دما (SST)، رنگ اقیانوس (کلروفیل) و کدورت آب ارائه می‌دهند."
                await callback.message.edit_text(msg, reply_markup=get_engineering_menu())

            # --- بازگشت به منوی اصلی ربات ---
            elif data == "back_to_main_bot":
                await callback.message.edit_text("👋 برای بازگشت به منوی اصلی ربات، لطفاً دکمه /start را بزنید.")

        except Exception as e:
            print(f"Ocean Error: {e}")
            if "message is not modified" not in str(e).lower():
                try: await callback.message.answer("❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.")
                except: pass

    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())