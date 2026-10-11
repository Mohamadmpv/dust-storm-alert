import asyncio
import os
import json
from datetime import datetime, timedelta
from baleio import Bot
from baleio.client.default import DefaultBotProperties
from baleio.enums import ParseMode
from config import BALE_TOKEN, BALE_CHAT_ID
from jalali import to_jalali, now_jalali


SEVERITY_EMOJI = {
    "CRITICAL": "[CRITICAL]",
    "SEVERE": "[SEVERE]",
    "MODERATE": "[MODERATE]",
    "WARNING": "[WARNING]",
}

HISTORY_FILE = "alert_history.json"
USERS_FILE = "users.json"
DUPLICATE_WINDOW_HOURS = 0


# ==================== خواندن کاربران ====================

def load_users():
    """خواندن Chat IDهای ثبت‌شده از users.json"""
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
        return list(users.keys())
    except Exception as e:
        print("Users load error:", e)
        return []


def get_all_chat_ids():
    """دریافت همه Chat IDها — فقط از BALE_CHAT_IDS"""
    chat_ids = []

    if BALE_CHAT_IDS:
        for cid in BALE_CHAT_IDS:
            cid = str(cid).strip()
            if cid and cid not in chat_ids:
                chat_ids.append(cid)

    print("DEBUG: Total chat_ids =", chat_ids)
    return chat_ids


# ==================== تاریخچه ====================

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("History save error:", e)


def make_key(alert):
    date_part = alert["time"][:10]
    return alert["point"] + "|" + date_part + "|" + alert["severity"]


def filter_new_alerts(alerts):
    history = load_history()
    now = datetime.now()
    cutoff = now - timedelta(hours=DUPLICATE_WINDOW_HOURS)

    new_alerts = []
    for a in alerts:
        key = make_key(a)
        last_sent_str = history.get(key)
        if last_sent_str:
            try:
                last_sent = datetime.fromisoformat(last_sent_str)
                if last_sent > cutoff:
                    continue
            except Exception:
                pass
        new_alerts.append(a)

    return new_alerts, history


def mark_as_sent(alerts, history):
    now_iso = datetime.now().isoformat()
    for a in alerts:
        history[make_key(a)] = now_iso
    save_history(history)


# ==================== پیام‌ها ====================

def format_alert_message(alerts):
    if not alerts:
        return None

    order = {"CRITICAL": 0, "SEVERE": 1, "MODERATE": 2, "WARNING": 3}
    alerts_sorted = sorted(alerts, key=lambda x: order.get(x["severity"], 4))

    grouped = {}
    for a in alerts_sorted:
        key = a["point"]
        if key not in grouped:
            grouped[key] = {
                "type": a.get("type", "internal"),
                "severity": a["severity"],
                "max_speed": a["speed"],
                "count": 0,
                "first_time": a["time"],
                "first_speed": a["speed"],
                "forecast": a.get("forecast"),
            }
        grouped[key]["count"] += 1
        if a["speed"] > grouped[key]["max_speed"]:
            grouped[key]["max_speed"] = a["speed"]

    internal = {k: v for k, v in grouped.items() if v["type"] == "internal"}
    external = {k: v for k, v in grouped.items() if v["type"] == "external"}

    msg = "🌪️ **هشدار طوفان گرد و خاک**\n\n"
    msg += "📅 " + now_jalali() + "\n"
    msg += "تعداد کل هشدارها: " + str(len(alerts)) + "\n"
    msg += "━━━━━━━━━━━━━━━\n\n"

    if internal:
        msg += "🇮🇷 **شهرها و دریاهای ایران**\n"
        msg += "━━━━━━━━━━━━━━━\n"
        for name, info in internal.items():
            emoji = SEVERITY_EMOJI.get(info["severity"], "")
            msg += "🔹 " + emoji + " **" + name + "**\n"
            msg += "   💨 احتمال باد با سرعت: " + str(info["first_speed"]) + " km/h\n"
            msg += "   🕐 اولین زمان: " + to_jalali(info["first_time"]) + "\n"
            if info.get("forecast"):
                fc = info["forecast"]
                if fc["next_time"] > info["first_time"]:
                    msg += "   🔮 پیش‌بینی: " + str(fc["next_speed"]) + " km/h در " + to_jalali(fc["next_time"]) + "\n"
            msg += "\n"

    if external:
        msg += "🌍 **منابع خارجی (احتمال حرکت به سمت ایران)**\n"
        msg += "━━━━━━━━━━━━━━━\n"
        for name, info in external.items():
            emoji = SEVERITY_EMOJI.get(info["severity"], "")
            msg += "🔸 " + emoji + " **" + name + "**\n"
            msg += "   💨 احتمال باد با سرعت: " + str(info["first_speed"]) + " km/h\n"
            msg += "   🕐 اولین زمان: " + to_jalali(info["first_time"]) + "\n"
            if info.get("forecast"):
                fc = info["forecast"]
                if fc["next_time"] > info["first_time"]:
                    msg += "   🔮 پیش‌بینی: " + str(fc["next_speed"]) + " km/h در " + to_jalali(fc["next_time"]) + "\n"
            msg += "\n"

    msg += "━━━━━━━━━━━━━━━\n"
    return msg


def format_forecast_message(forecasts):
    if not forecasts:
        return None

    msg = "🔮 **هشدار پیش‌بینانه طوفان**\n\n"
    msg += "📅 " + now_jalali() + "\n"
    msg += "باد در ساعت‌های آینده افزایش می‌یابد:\n"
    msg += "━━━━━━━━━━━━━━━\n\n"

    for f in forecasts:
        msg += "[WARNING] **" + f["point"] + "**\n"
        msg += "   🕐 زمان مورد انتظار: " + to_jalali(f["time"]) + "\n"
        msg += "   💨 سرعت باد: " + str(f["speed"]) + " km/h\n"
        msg += "   ⏳ حدود " + str(f["hours_until"]) + " ساعت دیگر\n"
        msg += "\n"

    msg += "━━━━━━━━━━━━━━━\n"
    return msg


# ==================== ارسال ====================

async def _send_to_all(message):
    """ارسال پیام به همه کاربران ثبت‌شده"""
    bot = Bot(
        token=BALE_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )

    chat_ids = get_all_chat_ids()
    print("  Total recipients:", len(chat_ids))

    success_count = 0
    fail_count = 0

    for chat_id in chat_ids:
        chat_id = str(chat_id).strip()
        if not chat_id:
            continue
        try:
            await bot.send_message(chat_id=chat_id, text=message)
            print("  ✅ Sent to:", chat_id)
            success_count += 1
        except Exception as e:
            print("  ❌ Failed to send to", chat_id, ":", e)
            fail_count += 1

    await bot.session.close()
    print("  Result:", success_count, "sent,", fail_count, "failed")


def send_alert(alerts):
    if not alerts:
        print("No alerts to send.")
        return False

    new_alerts, history = filter_new_alerts(alerts)

    if not new_alerts:
        print("All alerts are duplicates. Skipping.")
        return False

    print("New alerts (after dedup):", len(new_alerts), "of", len(alerts))

    message = format_alert_message(new_alerts)
    if not message:
        return False

    try:
        asyncio.run(_send_to_all(message))
        mark_as_sent(new_alerts, history)
        print("Alert sent to Bale.")
        return True
    except Exception as e:
        print("Send error:", e)
        return False


def send_forecast_alert(forecasts):
    if not forecasts:
        return False

    message = format_forecast_message(forecasts)
    if not message:
        return False

    try:
        asyncio.run(_send_to_all(message))
        print("Forecast sent to Bale.")
        return True
    except Exception as e:
        print("Send error:", e)
        return False


async def send_test_message():
    bot = Bot(
        token=BALE_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    chat_ids = get_all_chat_ids()
    print("Sending test to", len(chat_ids), "recipient(s)...")
    for chat_id in chat_ids:
        chat_id = str(chat_id).strip()
        if not chat_id:
            continue
        try:
            await bot.send_message(
                chat_id=chat_id,
                text="✅ تست اتصال - ربات ردیاب طوفان",
            )
            print("  ✅ Test sent to:", chat_id)
        except Exception as e:
            print("  ❌ Failed:", chat_id, e)
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(send_test_message())
    print("Test message sent.")