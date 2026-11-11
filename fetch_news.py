import sys
import requests
import xml.etree.ElementTree as ET
import re

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# --- منابع خبری ---
SOURCES = [
    {"name": "Nature Climate", "url": "https://www.nature.com/nclimate.rss", "type": "journal"},
    {"name": "ScienceDaily Ocean", "url": "https://www.sciencedaily.com/rss/earth_climate/oceanography.xml", "type": "journal"},
    {"name": "NOAA ENSO", "url": "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.txt", "type": "urgent"}
]

def clean_html(raw_html):
    if not raw_html: return ""
    clean = re.sub('<[^<]+?>', '', raw_html)
    return ' '.join(clean.split())[:400] + "..."

def get_news():
    """دریافت اخبار جدید برای ربات و ارسال زمان‌بندی شده"""
    news_list = []
    
    # 1. دریافت از ژورنال‌ها
    for src in SOURCES:
        if src["type"] == "journal":
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                r = requests.get(src["url"], headers=headers, timeout=15)
                r.raise_for_status()
                root = ET.fromstring(r.content)
                for item in root.findall('.//item')[:2]:
                    title = item.find('title')
                    link = item.find('link')
                    desc = item.find('description')
                    if title is not None and link is not None:
                        news_list.append({
                            "title": title.text,
                            "text": clean_html(desc.text) if desc is not None else "بدون توضیحات",
                            "link": link.text,
                            "source": src["name"]
                        })
            except Exception as e:
                print(f"Error fetching {src['name']}: {e}")

    # 2. دریافت از NOAA (متن ساده)
    try:
        r = requests.get(SOURCES[2]["url"], timeout=15)
        if r.status_code == 200:
            lines = r.text.split('\n')
            synopsis = ""
            for line in lines:
                if "Synopsis:" in line:
                    synopsis = line.replace("Synopsis:", "").strip()
                    break
            if synopsis:
                news_list.append({
                    "title": "🔴 به‌روزرسانی فوری NOAA (ال نینو)",
                    "text": synopsis[:400] + "...",
                    "link": "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/",
                    "source": "NOAA"
                })
    except Exception as e:
        print("Error fetching NOAA:", e)

    # اگر هیچ خبری نیامد، یک خبر پشتیبان
    if not news_list:
        news_list.append({
            "title": "پژوهش جدید در حوزه اقلیم",
            "text": "در حال حاضر ارتباط با سرورهای علمی برقرار نیست. لطفاً بعداً تلاش کنید.",
            "link": "https://www.nature.com/nclimate/",
            "source": "سیستم"
        })

    return news_list