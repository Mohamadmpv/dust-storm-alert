import os
import json
import requests
import asyncio
from jalali import now_jalali
from notifier import _send_to_all_async
from config import GIST_ID, GH_PAT

# --- مقالات علمی با چکیده ---
RESEARCH_ARTICLES = [
    {
        "id": 101,
        "title": "کاهش ذرات معلق انسان‌ساز به شروع سریع‌تر خشکسالی‌های ناگهانی کمک می‌کند",
        "journal": "Nature Communications",
        "year": "2026",
        "abstract": "خشکسالی‌های ناگهانی به عنوان مخاطرات شدید ظهور کرده‌اند. این مطالعه نشان می‌دهد که کاهش سطوح ذرات معلق (آئروسل‌ها) در یک اقلیم در حال گرم شدن، به شروع سریع‌تر خشکسالی‌های ناگهانی کمک می‌کند. اثرات آئروسل‌ها بر تغییرپذیری سرعت شروع در ۶۹.۲ درصد مناطق تشدید می‌شود. با کاهش انتشار آئروسل‌ها در آینده، منطقه در معرض خطر بالاتر تسریع خشکسالی تا ۱۱.۷ درصد در دوره ۲۰۷۰-۲۰۹۹ افزایش می‌یابد.",
        "link": "https://www.nature.com/articles/s41467-026-78230-4",
        "source": "Nature Communications"
    },
    {
        "id": 102,
        "title": "تغییر رژیم در رویدادهای مرکب خشکسالی-گرمای موج که خطرات اکوسیستم و تنش حرارتی را تشدید می‌کند",
        "journal": "Geophysical Research Letters (AGU)",
        "year": "2026",
        "abstract": "این مطالعه یک چارچوب دو مرحله‌ای برای مشخص کردن تکامل فرآیند روزانه در رویدادهای مرکب خشکسالی-گرمای موج (CDHEs) توسعه می‌دهد. چهار رژیم ترمودینامیکی شناسایی شده‌اند: آفتابی-مرطوب (۳۷٪)، آفتابی-خشک (۳۵٪)، همرفتی (۱۸٪) و آدیاباتیک (۱۰٪). نتایج نشان می‌دهد که خشکسالی-گرمای موج‌ها از حالت‌های ترمودینامیکی مختلفی بسته به شرایط آب‌وهوایی منطقه‌ای آغاز می‌شوند و مسیرهای تکاملی آن‌ها پیامدهای مهمی برای خطرات اکوسیستمی دارد.",
        "link": "https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2026GL125653",
        "source": "AGU Publications"
    }
]

# --- کتاب‌های پژوهشی اقلیم و آب‌وهوا ---
RESEARCH_BOOKS = [
    {
        "id": 201,
        "title": "Climate Dynamics (ویرایش دوم)",
        "author": "Kerry H. Cook",
        "publisher": "Princeton University Press",
        "year": "2025",
        "description": "کتابی جامع در مورد دینامیک اقلیم که مبانی فیزیکی سیستم اقلیمی، گردش عمومی جو و اقیانوس، و تعاملات مقیاس‌های مختلف را پوشش می‌دهد. مناسب برای دانشجویان تحصیلات تکمیلی و پژوهشگران.",
        "link": "https://press.princeton.edu/books/hardcover/9780691262352/climate-dynamics"
    },
    {
        "id": 202,
        "title": "The Physics of Climate Change",
        "author": "Lawrence M. Krauss",
        "publisher": "Head of Zeus",
        "year": "2024",
        "description": "این کتاب به زبان ساده اما دقیق، فیزیک پشت تغییرات اقلیمی را توضیح می‌دهد. شامل مباحثی مانند اثر گلخانه‌ای، تعادل انرژی زمین، و پیش‌بینی‌های مدل‌های اقلیمی.",
        "link": "https://www.headofzeus.com/books/the-physics-of-climate-change/9781804549346/"
    },
    {
        "id": 203,
        "title": "Mitigation and Adaptation Strategies Against Climate Change in Natural Systems",
        "author": "Rajiv Kumar Srivastava, Arun Chakraborty (Editors)",
        "publisher": "Springer",
        "year": "2025",
        "description": "این کتاب استراتژی‌های کاهش و سازگاری با تغییرات اقلیمی در سیستم‌های طبیعی را بررسی می‌کند. شامل بخش‌هایی در مورد زمین (کشاورزی، جنگل)، آب (رودخانه‌ها، دریاچه‌ها)، جو (هیدرولوژی، اقلیم) و فناوری‌های نوین (سنجش از دور، GIS، هوش مصنوعی).",
        "link": "https://link.springer.com/book/10.1007/978-3-031-75968-0"
    }
]

def get_sent_ids():
    """خواندن لیست آی‌دی‌های ارسال شده از Gist"""
    try:
        url = "https://api.github.com/gists/" + str(GIST_ID)
        headers = {"Authorization": "token " + str(GH_PAT)}
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        content = r.json()["files"].get("research_digest_memory.json", {}).get("content", "")
        return json.loads(content) if content else []
    except Exception as e:
        print("Gist read error:", e)
        return []

def save_sent_ids(new_ids):
    """ذخیره آی‌دی‌های ارسال شده در Gist"""
    try:
        url = "https://api.github.com/gists/" + str(GIST_ID)
        headers = {"Authorization": "token " + str(GH_PAT)}
        data = {"files": {"research_digest_memory.json": {"content": json.dumps(new_ids)}}}
        r = requests.patch(url, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        print("Memory updated in Gist.")
    except Exception as e:
        print("Gist write error:", e)

def build_message():
    sent_ids = get_sent_ids()
    new_ids = []
    
    msg = "📚 **مقالات و کتاب‌های پژوهشی اقلیم و آب‌وهوا** 📚\n\n"
    msg += "📅 " + now_jalali() + "\n"
    msg += "━━━━━━━━━━━━━━━\n\n"
    
    # بخش مقالات
    msg += "🔬 **مقالات علمی جدید (با چکیده):**\n\n"
    has_new_article = False
    for art in RESEARCH_ARTICLES:
        if art["id"] not in sent_ids:
            msg += f"**{art['title']}**\n"
            msg += f"📖 {art['journal']} ({art['year']})\n"
            msg += f"📝 **چکیده:** {art['abstract']}\n"
            msg += f"🔗 [لینک مقاله]({art['link']})\n\n"
            new_ids.append(art["id"])
            has_new_article = True
    
    if not has_new_article:
        msg += "   (مقاله جدیدی برای ارسال وجود ندارد)\n\n"
    
    # بخش کتاب‌ها
    msg += "━━━━━━━━━━━━━━━\n\n"
    msg += "📖 **کتاب‌های پژوهشی اقلیم و آب‌وهوا:**\n\n"
    has_new_book = False
    for book in RESEARCH_BOOKS:
        if book["id"] not in sent_ids:
            msg += f"**{book['title']}**\n"
            msg += f"✍️ {book['author']}\n"
            msg += f"🏢 {book['publisher']} ({book['year']})\n"
            msg += f"📝 {book['description']}\n"
            msg += f"🔗 [لینک کتاب]({book['link']})\n\n"
            new_ids.append(book["id"])
            has_new_book = True
    
    if not has_new_book:
        msg += "   (کتاب جدیدی برای ارسال وجود ندارد)\n\n"
    
    msg += "━━━━━━━━━━━━━━━\n"
    return msg, new_ids

async def main():
    print("=" * 60 + "\nگزارش پژوهشی اقلیم - " + now_jalali() + "\n" + "=" * 60)
    
    msg, new_ids = build_message()
    
    if new_ids:
        print(f"Sending {len(new_ids)} new research items.")
        await _send_to_all_async(msg)
        save_sent_ids(get_sent_ids() + new_ids)
    else:
        print("No new research items to send. Skipping to avoid spam.")
    
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())