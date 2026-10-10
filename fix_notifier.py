notifier_code = '''import asyncio
import os
import json
from datetime import datetime, timedelta
from baleio import Bot
from baleio.client.default import DefaultBotProperties
from baleio.enums import ParseMode
from config import BALE_TOKEN, BALE_CHAT_ID


SEVERITY_EMOJI = {
    "CRITICAL": "[CRITICAL]",
    "SEVERE": "[SEVERE]",
    "MODERATE": "[MODERATE]",
    "WARNING": "[WARNING]",
}

HISTORY_FILE = "alert_history.json"
DUPLICATE_WINDOW_HOURS = 0


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
                "forecast": a.get("forecast"),
            }
        grouped[key]["count"] += 1
        if a["speed"] > grouped[key]["max_speed"]:
            grouped[key]["max_speed"] = a["speed"]
        if a.get("forecast") and not grouped[key].get("forecast"):
            grouped[key]["forecast"] = a["forecast"]

    internal = {k: v for k, v in grouped.items() if v["type"] == "internal"}
    external = {k: v for k, v in grouped.items() if v["type"] == "external"}

    msg = "DUST STORM ALERT\\n\\n"
    msg += "Total alerts: " + str(len(alerts)) + "\\n"
    msg += "========================================\\n\\n"

    if internal:
        msg += "IRAN CITIES & SEAS:\\n"
        msg += "----------------------------------------\\n"
        for name, info in internal.items():
            emoji = SEVERITY_EMOJI.get(info["severity"], "")
            msg += emoji + " " + name + "\\n"
            msg += "  Alerts: " + str(info["count"]) + " | Max wind: " + str(info["max_speed"]) + " km/h\\n"
            if info.get("forecast"):
                fc = info["forecast"]
                msg += "  Forecast: " + str(fc["next_speed"]) + " km/h at " + fc["next_time"] + "\\n"
        msg += "\\n"

    if external:
        msg += "EXTERNAL SOURCES:\\n"
        msg += "----------------------------------------\\n"
        for name, info in external.items():
            emoji = SEVERITY_EMOJI.get(info["severity"], "")
            msg += emoji + " " + name + "\\n"
            msg += "  Alerts: " + str(info["count"]) + " | Max wind: " + str(info["max_speed"]) + " km/h\\n"
            if info.get("forecast"):
                fc = info["forecast"]
                msg += "  Forecast: " + str(fc["next_speed"]) + " km/h at " + fc["next_time"] + "\\n"
        msg += "\\n"

    msg += "========================================\\n"
    return msg


async def _send(message):
    bot = Bot(
        token=BALE_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    await bot.send_message(chat_id=BALE_CHAT_ID, text=message)
    await bot.session.close()


def send_alert(alerts):
    if not alerts:
        print("No alerts to send.")
        return False

    new_alerts, history = filter_new_alerts(alerts)

    if not new_alerts:
        print("All alerts are duplicates (sent within last 6 hours). Skipping.")
        return False

    print("New alerts (after dedup):", len(new_alerts), "of", len(alerts))

    message = format_alert_message(new_alerts)
    if not message:
        return False

    try:
        asyncio.run(_send(message))
        mark_as_sent(new_alerts, history)
        print("Alert sent to Bale:", len(new_alerts), "new alerts")
        return True
    except Exception as e:
        print("Send error:", e)
        return False


async def send_test_message():
    bot = Bot(
        token=BALE_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    await bot.send_message(
        chat_id=BALE_CHAT_ID,
        text="Test message from Dust Storm Alert Bot.",
    )
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(send_test_message())
    print("Test message sent.")
'''

with open("notifier.py", "w", encoding="utf-8") as f:
    f.write(notifier_code)

print("OK - notifier.py rewritten.")