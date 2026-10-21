import os
import json
import requests
import asyncio
from jalali import now_jalali
from notifier import _send_to_all_async
from config import GIST_ID, GH_PAT

# --- لیست اخبار پژوهشی و اقلیمی ---
CLIMATE_NEWS = [
    {
        "id": 1,
        "title": "مقاله پژوهشی (الزویر): تأثیر تقویت‌شده اقیانوس هند بر ال نینو",
        "text": "پژوهش جدیدی در ScienceDirect نشان می‌دهد که گرمایش جهانی باعث می‌شود اقیانوس هند تأثیر بسیار قوی‌تری بر ال نینو بگذارد. این یافته می‌تواند در آینده به پیش‌بینی دقیق‌تر ال نینو کمک کند.",
        "link": "https://www.sciencedirect.com/science/article/abs/pii/S0921818126004091",
        "source": "ScienceDirect"
    },
    {
        "id": 2,
        "title": "گزارش WMO: ال نینو تا فوریه ۲۰۲۷ ادامه دارد",
        "text": "سازمان جهانی هواشناسی (WMO) اعلام کرد که احتمال تداوم ال نینو تا فوریه ۲۰۲۷ نزدیک به ۱۰۰ درصد است. این پدیده ممکن است به یک «سوپر ال نینو» تبدیل شود و بر بارش‌های ایران نیز تأثیر بگذارد.",
        "link": "https://en.civilica.com/note/28059/",
        "source": "WMO / Civilica"
    },
    {
        "id": 3,
        "title": "هشدار ایسنا: احتمال سیل‌های ناگهانی در ایران با تشدید ال نینو",
        "text": "کارشناسان ایرانی هشدار می‌دهند که تشدید سوپر ال نینو و انحراف رودبادهای جوی، احتمال وقوع بارش‌های شدید و سیلاب‌های ناگهانی را در ایران افزایش می‌دهد.",
        "link": "https://media.isna.ir/news/1405071106476/",
        "source": "ایسنا"
    },
    {
        "id": 4,
        "title": "پژوهش جدید: ذوب یخ‌های قطب جنوب و تغییرات ناگهانی اقلیم",
        "text": "مطالعه‌ای در مجله Nature Climate Change نشان می‌دهد که سرعت ذوب یخ‌های قطب جنوب در سال ۲۰۲۶ رکورد زده است. این موضوع می‌تواند سطح آب دریاها را به طور قابل توجهی افزایش دهد و الگوهای آب‌وهوایی جهانی را دگرگون کند.",
        "link": "https://www.nature.com/nclimate/",
        "source": "Nature Climate Change"
    }
]

def get_sent_news_ids():
    try:
        url = "https://api.github.com/gists/" + str(GIST_ID)
        headers = {"Authorization": "token " + str(GH_PAT)}
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        content = r.json()["files"].get("sent_climate_news.json", {}).get("content", "")
        return json.loads(content) if content else []
    except Exception as e:
        print("Gist read error:", e)
        return []

def save_sent_news_ids(new_ids):
    try:
        url = "https://api.github.com/gists/" + str(GIST_ID)
        headers = {"Authorization": "token " + str(GH_PAT)}
        data = {"files": {"sent_climate_news.json": {"content": json.dumps(new_ids)}}}
        r = requests.patch(url, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        print("Gist updated with new sent news IDs.")
    except Exception as e:
        print("Gist write error:", e)

def build_news_message():
    sent_ids = get_sent_news_ids()
    new_ids_to_send = []
    
    msg = "🌍 **اخبار و مقالات پژوهشی اقلیم** 🌍\n\n"
    msg += "📅 " + now_jalali() + "\n"
    msg += "━━━━━━━━━━━━━━━\n\n"
    
    has_new = False
    for news in CLIMATE_NEWS:
        if news["id"] not in sent_ids:
            msg += f"🔹 **{news['title']}**\n"
            msg += f"   {news['text']}\n"
            msg += f"   🔗 [لینک خبر]({news['link']})\n"
            msg += f"   📌 منبع: {news['source']}\n\n"
            new_ids_to_send.append(news["id"])
            has_new = True
            
    if not has_new:
        msg += "در حال حاضر خبر پژوهشی جدیدی برای ارسال وجود ندارد.\n\n"
        
    msg += "━━━━━━━━━━━━━━━\n"
    return msg, new_ids_to_send

async def main():
    print("=" * 60 + "\nگزارش اخبار اقلیم - " + now_jalali() + "\n" + "=" * 60)
    msg, new_ids = build_news_message()
    
    if new_ids:
        print(f"Sending {len(new_ids)} new news items.")
        await _send_to_all_async(msg)
        save_sent_news_ids(get_sent_news_ids() + new_ids)
    else:
        print("No new news to send. Skipping to avoid spam.")
        
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())