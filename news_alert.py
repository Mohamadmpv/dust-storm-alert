import os
import sys
import json
import requests
import asyncio
import xml.etree.ElementTree as ET
import re
from jalali import now_jalali
from notifier import _send_to_all_async

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# --- ۱. منابع هشدار فوری (کامل) ---
URGENT_SOURCES = [
    {"name": "NOAA ENSO Advisory", "url": "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.txt", "link": "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/"},
    {"name": "WMO El Niño Update", "url": "https://wmo.int/", "link": "https://wmo.int/"},
]

# --- ۲. منابع علمی (کامل) ---
JOURNAL_SOURCES = [
    {"name": "JGR: Oceans", "url": "https://agupubs.onlinelibrary.wiley.com/feed/21699291/most-recent"},
    {"name": "Nature Climate Change", "url": "https://www.nature.com/nclimate.rss"},
    {"name": "Marine Pollution Bulletin", "url": "https://rss.sciencedirect.com/publication/science/0025326X"},
    {"name": "ScienceDaily Ocean", "url": "https://www.sciencedaily.com/rss/earth_climate/oceanography.xml"} 
]

# --- ۳. لیست پشتیبان (کامل و بدون کم شدن حتی یک مورد) ---
FALLBACK_NEWS = [
    {
        "id": "fb_elnino",
        "title": "🔴 هشدار فوری: ال نینو در حال تشدید است",
        "text": "مرکز پیش‌بینی اقلیم آمریکا (NOAA) اعلام کرد: ال نینو در حال تقویت است و احتمال یک رویداد «تاریخی» بین ۸۳ تا ۷۰ درصد است.",
        "link": "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/",
        "source": "NOAA"
    },
    {
        "id": "fb_coral",
        "title": "وضعیت مرجان‌های خلیج فارس",
        "text": "دمای آب در تابستان به بیش از ۳۶ درجه می‌رسد و مرجان‌ها در آستانه تنش حرارتی شدید هستند.",
        "link": "https://7sobh.com/",
        "source": "هفت صبح"
    },
    {
        "id": "fb_book",
        "title": "کتاب: Climate Dynamics (ویرایش دوم)",
        "text": "نویسنده: Kerry H. Cook | ناشر: Princeton University Press | سال: ۲۰۲۵ | این کتاب مبانی فیزیکی سیستم اقلیمی و گردش عمومی جو را پوشش می‌دهد.",
        "link": "https://press.princeton.edu/books/hardcover/9780691262352/climate-dynamics",
        "source": "Princeton University Press"
    }
]

SENT_NEWS_FILE = "sent_news.json"

def load_sent_news():
    """بارگذاری تاریخچه اخبار از فایل لوکال"""
    if os.path.exists(SENT_NEWS_FILE):
        try:
            with open(SENT_NEWS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_sent_news(sent_dict):
    """ذخیره تاریخچه در فایل لوکال (حداکثر ۲۰۰ مورد)"""
    if len(sent_dict) > 200:
        keys = list(sent_dict.keys())[-200:]
        sent_dict = {k: sent_dict[k] for k in keys}
    try:
        with open(SENT_NEWS_FILE, "w", encoding="utf-8") as f:
            json.dump(sent_dict, f, ensure_ascii=False)
    except Exception as e:
        print("Error saving news history:", e)

def clean_text(text, max_length=150):
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
            summary = clean_text(" ".join(important_lines[:2]), 150)
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
        for item in items[:2]: 
            title = item.find('title')
            guid = item.find('guid')
            link = item.find('link')
            final_link = guid.text if guid is not None and guid.text and ("http" in guid.text or "doi" in guid.text) else (link.text if link is not None else None)
            description = item.find('description')
            if title is not None and final_link is not None:
                desc_text = "بدون توضیحات"
                if description is not None and description.text:
                    desc_text = clean_text(description.text, 150)
                news_list.append({"title": clean_text(title.text, 100), "link": final_link, "description": desc_text, "source": source_name})
        return news_list
    except Exception as e:
        print(f"Error fetching {source_name}: {e}")
        return []

async def main():
    print("=" * 60)
    print("گزارش اخبار اقلیم و دریا - " + now_jalali())
    print("=" * 60)
    
    sent_news = load_sent_news()
    
    urgent_news = []
    for source in URGENT_SOURCES:
        urgent_news.extend(fetch_text_urgent(source["url"], source["name"]))
    
    journal_news = []
    for source in JOURNAL_SOURCES:
        journal_news.extend(fetch_rss_news(source["url"], source["name"]))
    
    def is_new(news):
        key = news.get("link") or news.get("title")
        return key not in sent_news

    new_urgent = [n for n in urgent_news if is_new(n)]
    new_journal = [n for n in journal_news if is_new(n)]
    
    fallback_news = []
    if not new_urgent and not new_journal:
        fallback_news = [n for n in FALLBACK_NEWS if n["id"] not in sent_news]
        for n in fallback_news:
            sent_news[n["id"]] = "sent"

    if new_urgent:
        msg = "🔴 **هشدارهای فوری اقلیمی** 🔴\n\n📅 " + now_jalali() + "\n━━━━━━━━━━━━━━━\n\n"
        for news in new_urgent:
            msg += f"\u200E🔹 \u202B**{news['title']}**\u202C\n   \u200E{news['description']}\n   🔗 [لینک منبع]({news['link']})\n   📌 منبع: {news['source']}\n\n"
            sent_news[news['link']] = "sent"
        msg += "━━━━━━━━━━━━━━━\n"
        await _send_to_all_async(msg)
        save_sent_news(sent_news)

    if new_journal:
        msg = "📚 **مقالات علمی معتبر (دریا و اقلیم)** 📚\n\n📅 " + now_jalali() + "\n━━━━━━━━━━━━━━━\n\n"
        for news in new_journal:
            msg += f"\u200E🔹 **{news['title']}**\n   \u200E{news['description']}\n   🔗 [مشاهده اصل مقاله]({news['link']})\n   📌 منبع: {news['source']}\n\n"
            sent_news[news['link']] = "sent"
        msg += "━━━━━━━━━━━━━━━\n"
        await _send_to_all_async(msg)
        save_sent_news(sent_news)

    if not new_urgent and not new_journal and fallback_news:
        msg = "📌 **اطلاعات آرشیوی (کتاب‌ها و پژوهش‌ها)** 📌\n\n📅 " + now_jalali() + "\n━━━━━━━━━━━━━━━\n\n"
        for news in fallback_news:
            msg += f"🔹 \u202B**{news['title']}**\u202C\n   \u202B{news['text']}\u202C\n   🔗 {news['link']}\n   📌 منبع: {news['source']}\n\n"
        msg += "━━━━━━━━━━━━━━━\n"
        await _send_to_all_async(msg)
        save_sent_news(sent_news)

    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())