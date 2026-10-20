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
        print("Gist read error:", e)
    return chat_ids

async def _send_to_all_async(msg):
    chat_ids = get_all_chat_ids()
    if not chat_ids: return

    if TELEGRAM_TOKEN:
        try:
            from telegram import Bot
            bot = Bot(token=TELEGRAM_TOKEN)
            for cid in chat_ids:
                try:
                    await bot.send_message(chat_id=cid, text=msg, parse_mode="Markdown")
                except Exception: pass
        except ImportError: pass

    if BALE_TOKEN:
        url = f"https://tapi.bale.ai/bot{BALE_TOKEN}/sendMessage"
        for cid in chat_ids:
            try:
                requests.post(url, json={"chat_id": cid, "text": msg, "parse_mode": "Markdown"}, timeout=30)
            except Exception: pass

def _send_to_all(msg):
    asyncio.run(_send_to_all_async(msg))

def send_alert(alerts):
    if not alerts: return
    msg = "🚨 **هشدار طوفان** 🚨\n\n"
    for a in alerts:
        msg += f"⚠️ **{a['point']}**\n   💨 سرعت باد: {a['speed']} km/h\n   🕐 زمان: {a['time']}\n\n"
    _send_to_all(msg)

def send_forecast_alert(forecasts):
    if not forecasts: return
    msg = "⚠️ **پیش‌بینی طوفان** ⚠️\n\n"
    for f in forecasts:
        msg += f"📍 **{f['point']}**\n   💨 سرعت: {f['speed']} km/h\n\n"
    _send_to_all(msg)

async def send_test_message():
    await _send_to_all_async("🧪 **پیام تست**\n\nسیستم هشدار کار می‌کند. ✅")