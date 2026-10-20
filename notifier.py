import os
import json
import asyncio
import requests
from config import BALE_TOKEN, TELEGRAM_TOKEN, GIST_ID, GH_PAT

def get_all_chat_ids():
    chat_ids = []
    try:
        if GIST_ID and GH_PAT:
            url = "https://api.github.com/gists/" + GIST_ID
            headers = {"Authorization": "token " + GH_PAT}
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            content = r.json()["files"].get("users.json", {}).get("content", "")
            if content:
                users = json.loads(content)
                for cid in users.keys():
                    cid = str(cid).strip()
                    if cid and cid not in chat_ids:
                        chat_ids.append(cid)
    except Exception as e:
        print("Gist read error in notifier:", e)
    return chat_ids

async def _send_to_all_async(msg):
    print("--- STARTING SEND PROCESS ---")
    chat_ids = get_all_chat_ids()
    print("Users found:", len(chat_ids), chat_ids)
    
    if not chat_ids:
        print("No chat IDs found. Exiting.")
        return

    if TELEGRAM_TOKEN:
        print("Attempting Telegram send...")
        try:
            from telegram import Bot
            bot = Bot(token=TELEGRAM_TOKEN)
            for cid in chat_ids:
                try:
                    # استفاده از ParseMode بدون مارک‌داون برای جلوگیری از خطا
                    await bot.send_message(chat_id=cid, text=msg)
                    print(f"TG Sent successfully to: {cid}")
                except Exception as e:
                    print(f"TG Failed for {cid}: {e}")
        except ImportError as e:
            print("Telegram module not installed:", e)
    else:
        print("TELEGRAM_TOKEN is missing!")

    if BALE_TOKEN:
        print("Attempting Bale send...")
        url = f"https://tapi.bale.ai/bot{BALE_TOKEN}/sendMessage"
        for cid in chat_ids:
            try:
                # بدون ParseMode برای جلوگیری از خطا
                r = requests.post(url, json={"chat_id": cid, "text": msg}, timeout=30)
                if r.status_code == 200:
                    print(f"Bale Sent successfully to: {cid}")
                else:
                    print(f"Bale Failed for {cid} - Status: {r.status_code} - Response: {r.text}")
            except Exception as e:
                print(f"Bale Failed for {cid}: {e}")
    else:
        print("BALE_TOKEN is missing!")
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