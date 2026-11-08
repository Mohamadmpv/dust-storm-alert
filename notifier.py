import os
import json
import asyncio
import requests
from config import BALE_TOKEN, TELEGRAM_TOKEN, GIST_ID, GH_PAT

def get_gist_data(filename):
    try:
        url = "https://api.github.com/gists/" + str(GIST_ID)
        headers = {"Authorization": "token " + str(GH_PAT)}
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        content = r.json()["files"].get(filename, {}).get("content", "")
        return json.loads(content) if content else {}
    except Exception as e:
        print(f"Gist read error ({filename}): {e}")
        return {}

def save_gist_data(filename, data):
    try:
        url = "https://api.github.com/gists/" + str(GIST_ID)
        headers = {"Authorization": "token " + str(GH_PAT)}
        gist_data = {"files": {filename: {"content": json.dumps(data)}}}
        r = requests.patch(url, headers=headers, json=gist_data, timeout=30)
        r.raise_for_status()
        print(f"Gist updated ({filename}).")
    except Exception as e:
        print(f"Gist write error ({filename}): {e}")

async def _send_to_all_async(msg, message_id=None):
    send_status = get_gist_data("send_status.json")
    
    if message_id is None:
        await _send_to_bale(msg)
        await _send_to_telegram(msg)
        return

    status = send_status.get(str(message_id), {"bale": False, "telegram": False})
    
    # ارسال به بله
    if BALE_TOKEN and not status["bale"]:
        success = await _send_to_bale(msg)
        if success:
            status["bale"] = True
            send_status[str(message_id)] = status
            save_gist_data("send_status.json", send_status)
            print(f"Bale status updated for {message_id}")

    # ارسال به تلگرام
    if TELEGRAM_TOKEN and not status["telegram"]:
        success = await _send_to_telegram(msg)
        if success:
            status["telegram"] = True
            send_status[str(message_id)] = status
            save_gist_data("send_status.json", send_status)
            print(f"Telegram status updated for {message_id}")

async def _send_to_bale(msg):
    users = get_gist_data("bale_users.json")
    if not users or not BALE_TOKEN:
        return False
    success = False
    url = f"https://tapi.bale.ai/bot{BALE_TOKEN}/sendMessage"
    for cid in users.keys():
        try:
            r = requests.post(url, json={"chat_id": cid, "text": msg}, timeout=30)
            if r.status_code == 200:
                print(f"Bale Sent: {cid}")
                success = True
            else:
                print(f"Bale Failed {cid}: {r.text}")
        except Exception as e:
            print(f"Bale Failed {cid}: {e}")
    return success

async def _send_to_telegram(msg):
    users = get_gist_data("telegram_users.json")
    if not users or not TELEGRAM_TOKEN:
        return False
    success = False
    try:
        from telegram import Bot
        bot = Bot(token=TELEGRAM_TOKEN)
        for cid in users.keys():
            try:
                await bot.send_message(chat_id=cid, text=msg)
                print(f"TG Sent: {cid}")
                success = True
            except Exception as e:
                print(f"TG Failed {cid}: {e}")
    except Exception as e:
        print(f"TG Error: {e}")
    return success

def _send_to_all(msg):
    asyncio.run(_send_to_all_async(msg))

def send_alert(alerts):
    if not alerts: return
    msg = "🚨 **هشدار طوفان** 🚨\n\n"
    for a in alerts:
        msg += f"⚠️ {a['point']}\n   💨 سرعت باد: {a['speed']} km/h\n   🕐 زمان: {a['time_tehran']}\n\n"
    _send_to_all(msg)

def send_forecast_alert(forecasts):
    if not forecasts: return
    msg = "⚠️ **پیش‌بینی طوفان** ⚠️\n\n"
    for f in forecasts:
        msg += f"📍 {f['point']}\n   💨 سرعت: {f['speed']} km/h\n\n"
    _send_to_all(msg)