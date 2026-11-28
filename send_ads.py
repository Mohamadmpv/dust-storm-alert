import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

BALE_TOKEN = os.getenv("BALE_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GIST_ID = os.getenv("GIST_ID")
GH_PAT = os.getenv("GH_PAT")

# --- تنظیمات تبلیغات ---
# مسیر عکسی که می‌خواهید ارسال شود (باید در پوشه پروژه باشد)
AD_IMAGE_PATH = "ad_image.jpg" 

# متن تبلیغاتی خود را اینجا بنویسید
AD_CAPTION = """
📢 **تبلیغات**
شرکت/محصول شما
توضیحات کوتاه
📞 راه ارتباطی
"""

def get_gist_data(filename):
    try:
        url = "https://api.github.com/gists/" + str(GIST_ID)
        headers = {"Authorization": "token " + str(GH_PAT)}
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        content = r.json()["files"].get(filename, {}).get("content", "")
        return json.loads(content) if content else {}
    except Exception as e:
        print(f"Error reading Gist: {e}")
        return {}

def send_ads():
    # بررسی وجود عکس
    if not os.path.exists(AD_IMAGE_PATH):
        print(f"❌ فایل عکس پیدا نشد: {AD_IMAGE_PATH}")
        return

    # ۱. ارسال به کاربران بله
    bale_users = get_gist_data("bale_users.json")
    if bale_users and BALE_TOKEN:
        print("Sending ads to Bale users...")
        url = f"https://tapi.bale.ai/bot{BALE_TOKEN}/sendPhoto"
        for cid in bale_users.keys():
            try:
                with open(AD_IMAGE_PATH, 'rb') as photo:
                    data = {"chat_id": cid, "caption": AD_CAPTION}
                    files = {"photo": photo}
                    r = requests.post(url, data=data, files=files, timeout=30)
                    if r.status_code == 200:
                        print(f"✅ Bale Sent to {cid}")
                    else:
                        print(f"❌ Bale Failed {cid}: {r.text}")
            except Exception as e:
                print(f"❌ Bale Error {cid}: {e}")

    # ۲. ارسال به کاربران تلگرام
    telegram_users = get_gist_data("telegram_users.json")
    if telegram_users and TELEGRAM_TOKEN:
        print("\nSending ads to Telegram users...")
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        for cid in telegram_users.keys():
            try:
                with open(AD_IMAGE_PATH, 'rb') as photo:
                    data = {"chat_id": cid, "caption": AD_CAPTION, "parse_mode": "Markdown"}
                    files = {"photo": photo}
                    r = requests.post(url, data=data, files=files, timeout=30)
                    if r.status_code == 200:
                        print(f"✅ Telegram Sent to {cid}")
                    else:
                        print(f"❌ Telegram Failed {cid}: {r.text}")
            except Exception as e:
                print(f"❌ Telegram Error {cid}: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("شروع ارسال تبلیغات...")
    print("=" * 50)
    send_ads()
    print("=" * 50)
    print("پایان.")