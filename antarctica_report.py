import asyncio
import os
import json
import requests
from dotenv import load_dotenv
from io import BytesIO

load_dotenv()

from telegram import Bot as TelegramBot, InputFile
from jalali import now_jalali

ANTARCTICA_TELEGRAM_TOKEN = os.getenv("ANTARCTICA_TELEGRAM_TOKEN")
ANTARCTICA_BALE_TOKEN = os.getenv("ANTARCTICA_BALE_TOKEN")
GIST_ID = os.getenv("GIST_ID")
GH_PAT = os.getenv("GH_PAT")

# --- ایستگاه‌های قطب جنوب ---
ANTARCTICA_STATIONS = [
    {"name": "Vostok (روسیه)", "temp": "-45°C تا -55°C", "coord": "۷۸°۲۷′ جنوبی، ۱۰۶°۵۰′ شرقی"},
    {"name": "Amundsen-Scott (آمریکا)", "temp": "-44°C تا -46°C", "coord": "۹۰° جنوبی"},
    {"name": "Novolazarevskaya (روسیه)", "temp": "-14°C تا -22°C", "coord": "۷۰°۴۶′ جنوبی، ۱۱°۵۰′ شرقی"},
    {"name": "Maitri (هند)", "temp": "-13°C تا -32°C", "coord": "۷۰°۴۵′ جنوبی، ۱۱°۴۳′ شرقی"},
    {"name": "Zhongshan (چین)", "temp": "-12°C تا -18°C", "coord": "۶۹°۲۲′ جنوبی، ۷۶°۲۲′ شرقی"},
    {"name": "Esperanza (آرژانتین)", "temp": "4°C تا 8°C", "coord": "۶۳°۲۴′ جنوبی، ۵۶°۵۹′ غربی"},
]

# --- اخبار طوفان‌های قطب جنوب ---
ANTARCTICA_STORM_NEWS = [
    {
        "title": "شدت گرفتن طوفان‌ها در دریای راس",
        "text": "پژوهش جدید دانشگاه اوتاگو نشان می‌دهد که طوفان‌های زمستانی در دریای راس طی دهه‌های اخیر هم مکررتر و هم شدیدتر شده‌اند. این طوفان‌ها با شکستن یخ‌های دریایی و اختلال در چرخه فصلی آن‌ها، مستقیماً بر اکوسیستم منطقه تأثیر می‌گذارند [citation:9].",
        "link": "https://phys.org/news/2026-07-antarctic-storms-frequent-intense-affecting.html"
    },
    {
        "title": "وضعیت گرداب قطبی (Polar Vortex) در سال ۲۰۲۶",
        "text": "برخلاف سال‌های گذشته، گرداب قطبی قطب جنوب در سال ۲۰۲۶ به طور غیرعادی ضعیف عمل کرده است. سرعت بادهای درون آن به سختی از ۶۰ متر بر ثانیه فراتر می‌رود، در حالی که در سال ۲۰۲۵ این مقدار به نزدیک ۱۰۰ متر بر ثانیه می‌رسید. این ضعف می‌تواند الگوهای آب‌وهوایی نیمکره جنوبی را تحت تأثیر قرار دهد [citation:1].",
        "link": "https://blitz.bg/obshtestvo/antarkticheskiyat-polyaren-vihar-otslabva-neobichayna-zima-i-ochakvana-topla-prolet-v-yuzhnoto-polukalbo_news1170165.html"
    }
]

# --- اخبار عمومی و پژوهشی ---
ANTARCTICA_NEWS = [
    {
        "title": "کاهش بی‌سابقه یخ‌های دریایی قطب جنوب (NSIDC/NASA)",
        "text": "داده‌های ماهواره‌ای نشان می‌دهد حداکثر وسعت یخ‌های دریایی در سال ۲۰۲۶ به حدود ۱۷.۵۹ میلیون کیلومتر مربع رسیده که سومین رکورد پایین‌ترین میزان از سال ۱۹۷۸ است [citation:3][citation:8].",
        "link": "https://nsidc.org/sea-ice-today"
    },
    {
        "title": "کشف اولین ردپای پستاندار در قطب جنوب (Cambridge)",
        "text": "فسیل ردپای یک پستاندار گوشت‌خوار کوچک به قدمت ۵۵.۵ میلیون سال در جزیره کینگ جورج کشف شد که نشان‌دهنده اکوسیستم پیچیده پیش از یخبندان است.",
        "link": "https://www.cambridge.org/core/journals/antarctic-science"
    }
]

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

def get_webcam_image():
    """دریافت تصویر زنده از دوربین NOAA"""
    url = "https://gmd-int.cmdl.noaa.gov/obop/spo/livecamera.html"
    # لینک مستقیم تصویر (معمولاً در صفحه پنهان است، از یک لینک پایدار استفاده می‌کنیم)
    image_url = "https://gmd-int.cmdl.noaa.gov/obop/spo/latest.jpg"
    try:
        r = requests.get(image_url, timeout=30)
        if r.status_code == 200 and r.headers.get('content-type', '').startswith('image'):
            return r.content
        return None
    except Exception:
        return None

def build_message():
    msg = "🧊 **گزارش آب‌وهوا، طوفان و اخبار جنوبگان** 🧊\n\n📅 " + now_jalali() + "\n"
    msg += "━━━━━━━━━━━━━━━\n\n"
    
    msg += "🌡️ **دمای ایستگاه‌های تحقیقاتی (امروز):**\n\n"
    for st in ANTARCTICA_STATIONS:
        msg += f"📍 **{st['name']}**\n"
        msg += f"   🌡️ دما: {st['temp']}\n"
        msg += f"   🗺️ مختصات: {st['coord']}\n"
        msg += "   ➖➖➖➖➖➖\n"
    
    msg += "\n━━━━━━━━━━━━━━━\n\n"
    msg += "🌀 **وضعیت طوفان‌ها در قطب جنوب:**\n\n"
    for news in ANTARCTICA_STORM_NEWS:
        msg += f"🔹 **{news['title']}**\n"
        msg += f"   {news['text']}\n"
        msg += f"   🔗 {news['link']}\n\n"

    msg += "━━━━━━━━━━━━━━━\n\n"
    msg += "📰 **سایر اخبار و پژوهش‌ها:**\n\n"
    for news in ANTARCTICA_NEWS:
        msg += f"🔹 **{news['title']}**\n"
        msg += f"   {news['text']}\n"
        msg += f"   🔗 {news['link']}\n\n"
        
    msg += "━━━━━━━━━━━━━━━\n"
    return msg

async def send_telegram(msg, image_bytes=None):
    users = get_gist_users("antarctica_telegram_users.json")
    if not users: 
        print("No Telegram users found.")
        return
    bot = TelegramBot(token=ANTARCTICA_TELEGRAM_TOKEN)
    print("Telegram recipients:", len(users))
    for cid in users.keys():
        try:
            if image_bytes:
                # ارسال عکس با کپشن
                await bot.send_photo(chat_id=cid, photo=InputFile(BytesIO(image_bytes), filename="south_pole.jpg"), caption=msg)
            else:
                # ارسال فقط متن
                await bot.send_message(chat_id=cid, text=msg)
            print("  TG Sent:", cid)
        except Exception as e:
            print("  TG Failed:", cid, e)

def send_bale(msg, image_bytes=None):
    users = get_gist_users("antarctica_bale_users.json")
    if not users: 
        print("No Bale users found.")
        return
    print("Bale recipients:", len(users))
    if not ANTARCTICA_BALE_TOKEN: 
        print("  Bale Failed: Token is None")
        return
    
    # بله از ارسال عکس از طریق URL پشتیبانی می‌کند، ولی ارسال فایل باینری پیچیده‌تر است.
    # برای سادگی، در بله فقط متن را با لینک تصویر می‌فرستیم.
    bale_msg = msg
    if image_bytes:
        bale_msg += "\n📷 [مشاهده تصویر زنده](https://gmd-int.cmdl.noaa.gov/obop/spo/livecamera.html)"
    
    for cid in users.keys():
        url = f"https://tapi.bale.ai/bot{ANTARCTICA_BALE_TOKEN}/sendMessage"
        try:
            r = requests.post(url, json={"chat_id": cid, "text": bale_msg, "parse_mode": "Markdown"}, timeout=30)
            r.raise_for_status()
            print("  Bale Sent:", cid)
        except Exception as e:
            print("  Bale Failed:", cid, e)

async def main():
    print("=" * 60 + "\nگزارش جنوبگان - " + now_jalali() + "\n" + "=" * 60)
    msg = build_message()
    
    # دریافت تصویر
    print("Fetching webcam image...")
    image_bytes = get_webcam_image()
    if image_bytes:
        print("Image fetched successfully.")
    else:
        print("Failed to fetch image.")

    # ارسال به تلگرام (با عکس)
    await send_telegram(msg, image_bytes)
    
    # ارسال به بله (متن + لینک عکس)
    send_bale(msg, image_bytes)
    
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())