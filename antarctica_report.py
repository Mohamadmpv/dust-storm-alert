import asyncio
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

from telegram import Bot as TelegramBot
from jalali import now_jalali

ANTARCTICA_TELEGRAM_TOKEN = os.getenv("ANTARCTICA_TELEGRAM_TOKEN")
ANTARCTICA_BALE_TOKEN = os.getenv("ANTARCTICA_BALE_TOKEN")
GIST_ID = os.getenv("GIST_ID")
GH_PAT = os.getenv("GH_PAT")

# --- داده‌های قطب جنوب ---
ANTARCTICA_WEBCAM = {
    "name": "دوربین زنده ایستگاه Amundsen-Scott (NOAA)",
    "link": "https://gmd-int.cmdl.noaa.gov/obop/spo/livecamera.html"
}

ANTARCTICA_STATIONS = [
    {"name": "Vostok (روسیه)", "temp": "-45°C تا -55°C", "coord": "۷۸°۲۷′ جنوبی، ۱۰۶°۵۰′ شرقی", "source": "weather.com.cn "},
    {"name": "Amundsen-Scott (آمریکا)", "temp": "-44°C تا -46°C", "coord": "۹۰° جنوبی", "source": "MeteoNews "},
    {"name": "Novolazarevskaya (روسیه)", "temp": "-14°C تا -22°C", "coord": "۷۰°۴۶′ جنوبی، ۱۱°۵۰′ شرقی", "source": "meteoblue "},
    {"name": "Maitri (هند)", "temp": "-13°C تا -32°C", "coord": "۷۰°۴۵′ جنوبی، ۱۱°۴۳′ شرقی", "source": "meteoblue "},
    {"name": "Zhongshan (چین)", "temp": "-12°C تا -18°C", "coord": "۶۹°۲۲′ جنوبی، ۷۶°۲۲′ شرقی", "source": "weather.com.cn "},
    {"name": "Esperanza (آرژانتین)", "temp": "4°C تا 8°C", "coord": "۶۳°۲۴′ جنوبی، ۵۶°۵۹′ غربی", "source": "CruisePlanners "},
]

ANTARCTICA_NEWS = [
    {
        "title": "ناوگان کشتی‌های بدون سرنشین برای مطالعه CO2 اقیانوس جنوبی به دور قطب جنوب می‌روند",
        "paragraph": "پروژه COCO2 به رهبری NOAA و مشارکت CSIRO استرالیا، از ۱۹ سپتامبر ۲۰۲۶ با اعزام اولین کشتی بدون سرنشین Saildrone از هوبارت آغاز شد. هدف این ماموریت ۵ ساله، اندازه‌گیری میزان جذب دی‌اکسید کربن توسط اقیانوس جنوبی به ویژه در فصل زمستان است که با کشتی‌های سنتی امکان‌پذیر نیست. این کشتی‌ها به صورت خودکار مسیر خود را دور قطب جنوب طی می‌کنند و داده‌های ارزشمندی برای مدل‌های اقلیمی ارسال می‌کنند.",
        "link": "https://www.pmel.noaa.gov/news-and-media/highlights/saildrone-research-fleet-circle-antarctica-5-years"
    },
    {
        "title": "اکتشافات باستان‌شناسی زیر آب در قطب جنوب برای اولین بار",
        "paragraph": "سی و پنجمین سفر تحقیقاتی بلغارستان به قطب جنوب، شامل اولین پروژه باستان‌شناسی زیر آب این کشور خواهد بود. تیم تحقیقاتی قصد دارد با استفاده از سونار و ربات‌های زیرآبی، بقایای کشتی‌های غرق شده در آب‌های کم‌عمق اطراف قطب جنوب را شناسایی کند. با توجه به دمای بسیار پایین آب، احتمال سالم ماندن این بقایا بالاست. این پروژه همچنین به مطالعه فعالیت‌های آتشفشانی و لرزه‌ای در جزایر شتلند جنوبی خواهد پرداخت.",
        "link": "https://www.bta.bg/en/news/1226848-35th-bulgarian-antarctic-expedition-to-expand-scientific-work-at-base-and-aboard"
    }
]

PENGUIN_NEWS = [
    "🐧 **هشدار جدی (اکتبر ۲۰۲۶):** بزرگ‌ترین کلنی پنگوئن‌های چین‌استرپ در جزیره زاوودوفسکی از سال ۲۰۱۱ تاکنون **۶۳ درصد** کاهش یافته است. علت: کاهش کریل به دلیل گرمایش اقیانوس‌ها.",
    "🦠 **حیات بی‌مهرگان جنوبگان:** گونه‌هایی از هیره‌های میکروسکوپی مانند *Alaskozetes antarcticus* تا عرض ۷۱ درجه جنوبی یافت می‌شوند. مگس‌ریزه بدون پرواز *Belgica antarctica* (۶ میلی‌متر) بزرگ‌ترین جانور کاملاً زمینی جنوبگان است.",
    "🦐 **کریل جنوبگان (*Euphausia superba*):** غذای اصلی نهنگ‌ها، فک‌ها و پنگوئن‌ها، در اقیانوس جنوبی زندگی می‌کند و توانایی شگفت‌انگیزی در کاهش اندازه بدن برای زنده ماندن در زمستان دارد."
]

# --- توابع ---
def get_gist_users(filename):
    url = "https://api.github.com/gists/" + str(GIST_ID)
    headers = {"Authorization": "token " + str(GH_PAT)}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        content = r.json()["files"].get(filename, {}).get("content", "")
        return json.loads(content) if content else {}
    except Exception as e:
        print("Gist error:", e)
        return {}

def build_message():
    msg = "🧊 **گزارش روزانه قطب جنوب** 🧊\n\n📅 " + now_jalali() + "\n"
    msg += "━━━━━━━━━━━━━━━\n\n"
    
    msg += f"📹 **{ANTARCTICA_WEBCAM['name']}:**\n   🔗 {ANTARCTICA_WEBCAM['link']}\n\n"
    
    msg += "🌡️ **دمای ایستگاه‌های تحقیقاتی (امروز):**\n"
    for st in ANTARCTICA_STATIONS:
        msg += f"   • **{st['name']}**\n     دما: {st['temp']}\n     مختصات: {st['coord']}\n     منبع: {st['source']}\n"
    msg += "\n"

    if PENGUIN_NEWS:
        msg += "🐾 **اخبار حیات وحش:**\n"
        for news in PENGUIN_NEWS:
            msg += f"   {news}\n\n"

    msg += "📰 **اخبار پژوهشی جدید:**\n\n"
    for item in ANTARCTICA_NEWS:
        msg += f"**{item['title']}**\n"
        msg += f"{item['paragraph']}\n"
        msg += f"🔗 {item['link']}\n\n"
        
    msg += "━━━━━━━━━━━━━━━\n"
    return msg

async def send_telegram(msg):
    users = get_gist_users("antarctica_telegram_users.json")
    if not users: return
    bot = TelegramBot(token=ANTARCTICA_TELEGRAM_TOKEN)
    print("Telegram recipients:", len(users))
    for cid in users.keys():
        try:
            await bot.send_message(chat_id=cid, text=msg)
            print("  TG Sent:", cid)
        except Exception as e:
            print("  TG Failed:", cid, e)

def send_bale(msg):
    users = get_gist_users("antarctica_bale_users.json")
    if not users: return
    print("Bale recipients:", len(users))
    if not ANTARCTICA_BALE_TOKEN: return
    for cid in users.keys():
        url = f"https://tapi.bale.ai/bot{ANTARCTICA_BALE_TOKEN}/sendMessage"
        try:
            r = requests.post(url, json={"chat_id": cid, "text": msg, "parse_mode": "Markdown"}, timeout=30)
            r.raise_for_status()
            print("  Bale Sent:", cid)
        except Exception as e:
            print("  Bale Failed:", cid, e)

async def main():
    print("=" * 60 + "\nگزارش قطب جنوب - " + now_jalali() + "\n" + "=" * 60)
    msg = build_message()
    await send_telegram(msg)
    send_bale(msg)
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())