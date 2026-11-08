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

# --- منابع هشدار فوری و خبری (اولویت اول) ---
URGENT_SOURCES = [
    # هشدارهای رسمی NOAA درباره ال نینو (لینک مستقیم به صفحه به‌روزرسانی)
    {"name": "NOAA ENSO Advisory", "url": "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.txt", "type": "urgent", "link": "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/"},
    # هشدارهای سازمان جهانی هواشناسی
    {"name": "WMO El Niño Update", "url": "https://wmo.int/", "type": "urgent", "link": "https://wmo.int/"},
]

# --- منابع خبری معتبر (اولویت دوم) ---
NEWS_SOURCES = [
    {"name": "خبرگزاری صداوسیما (هواشناسی)", "url": "https://www.iribnews.ir/fa/rss", "type": "news"},
    {"name": "ایسنا (محیط زیست)", "url": "https://www.isna.ir/rss", "type": "news"},
]

# --- منابع علمی معتبر (اولویت سوم) ---
JOURNAL_SOURCES = [
    {"name": "JGR: Oceans", "url": "https://agupubs.onlinelibrary.wiley.com/feed/21699291/most-recent", "type": "journal"},
    {"name": "Marine Pollution Bulletin", "url": "https://rss.sciencedirect.com/publication/science/0025326X", "type": "journal"},
]

# --- اخبار پشتیبان (اگر اینترنت قطع بود) ---
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

def fetch_text_urgent(url, source_name):
    """دریافت متن ساده از منابع هشدار (مثل NOAA)"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        text = r.text
        
        # استخراج خطوط مهم (مثلاً Synopsis یا Summary)
        lines = text.split('\n')
        important_lines = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ['synopsis:', 'el niño', 'el nino', 'chance', 'probability']):
                important_lines.append(line.strip())
        
        if important_lines:
            summary = " ".join(important_lines[:3])  # ۳ خط اول مهم
            return [{"title": f"🔴 {source_name}: به‌روزرسانی فوری", "description": summary[:300] + "...", "link": url, "source": source_name}]
        return []
    except Exception as e:
        print(f"Error fetching {source_name}: {e}")
        return []

def fetch_rss_news(source_url, source_name, source_type):
    """دریافت خبر از فید RSS"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(source_url, headers=headers, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = root.findall('.//item')
        news_list = []
        for item in items[:2]:  # فقط ۲ خبر آخر
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
                    clean_desc = re.sub('<[^<]+?>', '', description.text)
                    desc_text = clean_desc[:150] + "..."
                news_list.append({
                    "title": title.text,
                    "link": final_link,
                    "description": desc_text,
                    "source": source_name,
                    "type": source_type
                })
        return news_list
    except Exception as e:
        print(f"Error fetching {source_name}: {e}")
        return []

def get_sent_news_urls():
    try:
        url = "https://api.github.com/gists/" + str(GIST_ID)
        headers = {"Authorization": "token " + str(GH_PAT)}
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        content = r.json()["files"].get("sent_news_urls.json", {}).get("content", "")
        return json.loads(content) if content else []
    except Exception as e:
        print(f"Gist read error: {e}")
        return []

def save_sent_news_urls(new_urls):
    try:
        url = "https://api.github.com/gists/" + str(GIST_ID)
        headers = {"Authorization": "token " + str(GH_PAT)}
        data = {"files": {"sent_news_urls.json": {"content": json.dumps(new_urls)}}}
        r = requests.patch(url, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        print("Gist memory updated.")
    except Exception as e:
        print(f"Gist write error: {e}")

def build_news_message():
    sent_urls = get_sent_news_urls()
    new_urls = []
    urgent_news = []
    online_news = []
    journal_news = []
    
    # ۱. منابع هشدار فوری (NOAA / WMO)
    for source in URGENT_SOURCES:
        print(f"Checking urgent source: {source['name']}...")
        items = fetch_text_urgent(source["url"], source["name"])
        for item in items:
            if item["link"] not in sent_urls:
                urgent_news.append(item)
                new_urls.append(item["link"])
    
    # ۲. منابع خبری معتبر
    for source in NEWS_SOURCES:
        print(f"Fetching news from {source['name']}...")
        items = fetch_rss_news(source["url"], source["name"], "news")
        for item in items:
            if item["link"] not in sent_urls:
                online_news.append(item)
                new_urls.append(item["link"])
    
    # ۳. منابع علمی (ژورنال‌ها)
    for source in JOURNAL_SOURCES:
        print(f"Fetching journal: {source['name']}...")
        items = fetch_rss_news(source["url"], source["name"], "journal")
        for item in items:
            if item["link"] not in sent_urls:
                journal_news.append(item)
                new_urls.append(item["link"])
    
    # ۴. اگر هیچ خبری آنلاین نبود، از لیست پشتیبان استفاده کن
    fallback_news = []
    if not urgent_news and not online_news and not journal_news:
        print("No online news. Using fallback.")
        for news in FALLBACK_NEWS:
            if news["id"] not in sent_urls:
                fallback_news.append(news)
                new_urls.append(news["id"])
    
    # ۵. ساخت پیام (اولویت‌بندی شده)
    msg = "🌍 **اخبار و هشدارهای اقلیم و دریا** 🌍\n\n"
    msg += "📅 " + now_jalali() + "\n"
    msg += "━━━━━━━━━━━━━━━\n\n"
    
    if urgent_news:
        msg += "🔴 **هشدارهای فوری (ال نینو / اقلیم):**\n\n"
        for news in urgent_news:
            msg += f"🔹 **{news['title']}**\n"
            msg += f"   {news['description']}\n"
            msg += f"   🔗 [لینک منبع]({news['link']})\n"
            msg += f"   📌 منبع: {news['source']}\n\n"
    
    if online_news:
        msg += "📰 **اخبار معتبر اقلیمی و دریایی:**\n\n"
        for news in online_news:
            msg += f"🔹 **{news['title']}**\n"
            msg += f"   {news['description']}\n"
            msg += f"   🔗 [لینک خبر]({news['link']})\n"
            msg += f"   📌 منبع: {news['source']}\n\n"
    
    if journal_news:
        msg += "📚 **مقالات علمی جدید:**\n\n"
        for news in journal_news:
            msg += f"🔹 **{news['title']}**\n"
            msg += f"   {news['description']}\n"
            msg += f"   🔗 [مشاهده اصل مقاله]({news['link']})\n"
            msg += f"   📌 منبع: {news['source']}\n\n"
    
    if fallback_news:
        msg += "📌 **اطلاعات آرشیوی (دریایی و اقلیمی):**\n\n"
        for news in fallback_news:
            msg += f"🔹 {news['title']}\n"
            msg += f"   {news['text']}\n"
            msg += f"   🔗 {news['link']}\n"
            msg += f"   📌 منبع: {news['source']}\n\n"
    
    if not new_urls:
        msg += "در حال حاضر خبر یا مقاله جدیدی برای ارسال وجود ندارد.\n\n"
    
    msg += "━━━━━━━━━━━━━━━\n"
    return msg, new_urls

async def main():
    print("=" * 60)
    print("گزارش اخبار اقلیم و دریا - " + now_jalali())
    print("=" * 60)
    
    msg, new_urls = build_news_message()
    
    if new_urls:
        print(f"Sending {len(new_urls)} new items.")
        await _send_to_all_async(msg)
        save_sent_news_urls(get_sent_news_urls() + new_urls)
    else:
        print("No new items to send. Skipping to avoid spam.")
        
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())