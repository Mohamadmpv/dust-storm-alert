import os
import sys
import json
import requests
import asyncio
import xml.etree.ElementTree as ET
import re
from jalali import now_jalali
from notifier import _send_to_all_async
from config import GIST_ID, GH_PAT

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# --- ۱. منابع هشدار فوری (اولویت اول) ---
URGENT_SOURCES = [
    {"name": "NOAA ENSO Advisory", "url": "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.txt", "link": "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/"},
    {"name": "WMO El Niño Update", "url": "https://wmo.int/", "link": "https://wmo.int/"},
]

# --- ۲. منابع علمی معتبر (اولویت دوم) ---
JOURNAL_SOURCES = [
    {"name": "JGR: Oceans", "url": "https://agupubs.onlinelibrary.wiley.com/feed/21699291/most-recent"},
    {"name": "Marine Pollution Bulletin", "url": "https://rss.sciencedirect.com/publication/science/0025326X"},
    {"name": "Ocean & Coastal Management", "url": "https://rss.sciencedirect.com/publication/science/09645691"},
]

# --- ۳. لیست پشتیبان (اگر هیچ خبری آنلاین نبود) ---
FALLBACK_NEWS = [
    {
        "id": "fb_elnino",
        "title": "🔴 هشدار فوری: ال نینو در حال تشدید است (NOAA - اکتبر ۲۰۲۶)",
        "text": "مرکز پیش‌بینی اقلیم آمریکا (NOAA) اعلام کرد: ال نینو در حال تقویت است و احتمال یک رویداد «تاریخی» (قوی‌تر از تمام رکوردهای ۱۹۵۰) بین ۸۳ تا ۷۰ درصد است. سازمان هواشناسی ایران نیز هشدار داده که این پدیده بارش‌ها را سیل‌آسا و نقطه‌ای می‌کند.",
        "link": "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/",
        "source": "NOAA / سازمان هواشناسی"
    },
    {
        "id": "fb_coral",
        "title": "وضعیت مرجان‌های خلیج فارس",
        "text": "رئیس مرکز اقیانوس‌شناسی خلیج فارس: دمای آب در تابستان به بیش از ۳۶ درجه می‌رسد و مرجان‌ها در آستانه تنش حرارتی شدید هستند. گرمایش اقیانوس‌ها زنجیره غذایی را تهدید می‌کند.",
        "link": "https://7sobh.com/",
        "source": "هفت صبح"
    }
]

def clean_text(text, max_length=500):
    if not text: return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = ' '.join(text.split())
    if len(text) > max_length:
        text = text[:max_length] + "..."
    return text.strip()

def fetch_text_urgent(url, source_name):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        text = r.text
        lines = text.split('\n')
        important_lines = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ['synopsis:', 'el niño', 'el nino', 'chance', 'probability']):
                important_lines.append(line.strip())
        
        if important_lines:
            summary = clean_text(" ".join(important_lines[:5]), 500)
            return [{"title": f"🔴 {source_name}: به‌روزرسانی فوری", "description": summary, "link": url, "source": source_name}]
        return []
    except Exception as e:
        print(f"Error fetching {source_name}: {e}")
        return []

def fetch_rss_news(source_url, source_name):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(source_url, headers=headers, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = root.findall('.//item')
        news_list = []
        for item in items[:3]:
            title = item.find('title')
            guid = item.find('guid')
            link = item.find('link')
            
            final_link = None
            if guid is not None and guid.text and ("http" in guid.text or "doi" in guid.text):
                final_link = guid.text
            elif link is not None and link.text:
                final_link = link.text
            
            description = item.find('description')
            
            if title is not None and final_link is not None:
                desc_text = "بدون توضیحات"
                if description is not None and description.text:
                    desc_text = clean_text(description.text, 500)
                news_list.append({
                    "title": clean_text(title.text, 200),
                    "link": final_link,
                    "description": desc_text,
                    "source": source_name
                })
        return news_list
    except Exception as e:
        print(f"Error fetching {source_name}: {e}")
        return []

async def main():
    print("=" * 60)
    print("گزارش اخبار اقلیم و دریا - " + now_jalali())
    print("=" * 60)
    
    # ۱. جمع‌آوری هشدارهای فوری
    urgent_news = []
    for source in URGENT_SOURCES:
        print(f"Checking urgent source: {source['name']}...")
        urgent_news.extend(fetch_text_urgent(source["url"], source["name"]))
    
    # ۲. جمع‌آوری مقالات علمی
    journal_news = []
    for source in JOURNAL_SOURCES:
        print(f"Fetching journal: {source['name']}...")
        journal_news.extend(fetch_rss_news(source["url"], source["name"]))
    
    # ۳. اگر هیچ خبری آنلاین نبود، از لیست پشتیبان استفاده کن
    fallback_news = []
    if not urgent_news and not journal_news:
        print("No online news. Using fallback.")
        fallback_news = FALLBACK_NEWS

    # ۴. ارسال پیام‌ها
    if urgent_news:
        msg = "🔴 **هشدارهای فوری اقلیمی** 🔴\n\n"
        msg += "📅 " + now_jalali() + "\n━━━━━━━━━━━━━━━\n\n"
        for news in urgent_news:
            msg += f"\u200E🔹 \u202B**{news['title']}**\u202C\n"
            msg += f"   \u200E{news['description']}\n"
            msg += f"   🔗 [لینک منبع]({news['link']})\n"
            msg += f"   📌 منبع: {news['source']}\n\n"
        msg += "━━━━━━━━━━━━━━━\n"
        print("Sending urgent news...")
        await _send_to_all_async(msg, message_id=f"urgent_{urgent_news[0]['link']}")

    if journal_news:
        msg = "📚 **مقالات علمی معتبر (دریا و اقلیم)** 📚\n\n"
        msg += "📅 " + now_jalali() + "\n━━━━━━━━━━━━━━━\n\n"
        for news in journal_news:
            msg += f"\u200E🔹 **{news['title']}**\n"
            msg += f"   \u200E{news['description']}\n"
            msg += f"   🔗 [مشاهده اصل مقاله]({news['link']})\n"
            msg += f"   📌 منبع: {news['source']}\n\n"
        msg += "━━━━━━━━━━━━━━━\n"
        print("Sending journal news...")
        await _send_to_all_async(msg, message_id=f"journal_{journal_news[0]['link']}")

    # اگر هیچ خبری ارسال نشد، حتماً فال‌بک را بفرست
    if not urgent_news and not journal_news and fallback_news:
        msg = "📌 **اطلاعات آرشیوی (دریایی و اقلیمی)** 📌\n\n"
        msg += "📅 " + now_jalali() + "\n━━━━━━━━━━━━━━━\n\n"
        for news in fallback_news:
            msg += f"🔹 \u202B**{news['title']}**\u202C\n"
            msg += f"   \u202B{news['text']}\u202C\n"
            msg += f"   🔗 {news['link']}\n"
            msg += f"   📌 منبع: {news['source']}\n\n"
        msg += "━━━━━━━━━━━━━━━\n"
        print("Sending fallback news...")
        await _send_to_all_async(msg, message_id=f"fallback_{fallback_news[0]['id']}")

    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())