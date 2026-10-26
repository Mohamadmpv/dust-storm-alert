import os
import json
import asyncio
import requests
from config import BALE_TOKEN, TELEGRAM_TOKEN, GIST_ID, GH_PAT

def get_users_from_gist(filename):
    chat_ids = []
    try:
        if GIST_ID and GH_PAT:
            url = "https://api.github.com/gists/" + GIST_ID
            headers = {"Authorization": "token " + GH_PAT}
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            content = r.json()["files"].get(filename, {}).get("content", "")
            if content:
                users = json.loads(content)
                for cid in users.keys():
                    cid = str(cid).strip()
                    if cid and cid not in chat_ids:
                        chat_ids.append(cid)
    except Exception as e:
        print(f"Gist read error ({filename}):", e)
    return chat_ids

async def _send_to_all_async(msg):
    print("--- STARTING SEND PROCESS ---")
    
    # خواندن لیست‌های جداگانه
    tg_chat_ids = get_users_from_gist("telegram_users.json")
    bale_chat_ids = get_users_from_gist("bale_users.json")
    
    print(f"Telegram users: {len(tg_chat_ids)} | Bale users: {len(bale_chat_ids)}")

    # ارسال به تلگرام
    if TELEGRAM_TOKEN and tg_chat_ids:
        print("Attempting Telegram send...")
        try:
            from telegram import Bot
            bot = Bot(token=TELEGRAM_TOKEN)
            for cid in tg_chat_ids:
                try:
                    # تلاش اول با مارک‌داون
                    await bot.send_message(chat_id=cid, text=msg, parse_mode="Markdown")
                    print(f"TG Sent successfully to: {cid}")
                except Exception as e:
                    print(f"TG Markdown failed for {cid}: {e}")
                    try:
                        # اگر مارک‌داون خطا داد، بدون فرمت بفرست
                        await bot.send_message(chat_id=cid, text=msg)
                        print(f"TG Sent (no format) successfully to: {cid}")
                    except Exception as e2:
                        print(f"TG Failed completely for {cid}: {e2}")
        except ImportError as e:
            print("Telegram module not installed:", e)
    else:
        print("Telegram skipped (No token or no users).")

    # 2. ارسال به بله
    if BALE_TOKEN and bale_chat_ids:
        print("Attempting Bale send...")
        url = f"https://tapi.bale.ai/bot{BALE_TOKEN}/sendMessage"
        for cid in bale_chat_ids:
            try:
                r = requests.post(url, json={"chat_id": cid, "text": msg}, timeout=30)
                if r.status_code == 200:
                    print(f"Bale Sent successfully to: {cid}")
                else:
                    print(f"Bale Failed for {cid} - Response: {r.text}")
            except Exception as e:
                print(f"Bale Failed for {cid}: {e}")
    else:
        print("Bale skipped (No token or no users).")
        
    print("--- SEND PROCESS FINISHED ---")

def _send_to_all(msg):
    asyncio.run(_send_to_all_async(msg))

def send_alert(alerts):
    if not alerts: return
    msg = "🚨 هشدار طوفان 🚨\n\n"
    for a in alerts:
        msg += f"⚠️ {a['point']}\n   💨 سرعت باد: {a['speed']} km/h\n   🕐 زمان: {a['time']}\n\n"
    _send_to_all(msg)

def send_forecast_alert(forecasts):
    if not forecasts: return
    msg = "⚠️ پیش‌بینی طوفان ⚠️\n\n"
    for f in forecasts:
        msg += f"📍 {f['point']}\n   💨 سرعت: {f['speed']} km/h\n\n"
    _send_to_all(msg)

async def send_test_message():
    await _send_to_all_async("🧪 پیام تست\n\nسیستم هشدار کار می‌کند. ✅")