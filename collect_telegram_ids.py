import os
import json
import asyncio
import requests
from telegram import Bot


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GIST_ID = os.getenv("GIST_ID")
GH_PAT = os.getenv("GH_PAT")


def get_gist_file(filename):
    url = "https://api.github.com/gists/" + GIST_ID
    headers = {"Authorization": "token " + GH_PAT}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()["files"].get(filename, {}).get("content", "")
    except Exception as e:
        print("Gist read error:", e)
        return ""


def save_gist_file(filename, content):
    url = "https://api.github.com/gists/" + GIST_ID
    headers = {"Authorization": "token " + GH_PAT}
    data = {"files": {filename: {"content": content}}}
    try:
        r = requests.patch(url, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        return True
    except Exception as e:
        print("Gist write error:", e)
        return False


def get_gist_users():
    content = get_gist_file("users.json")
    try:
        return json.loads(content) if content else {}
    except Exception:
        return {}


def save_gist_users(users):
    return save_gist_file("users.json", json.dumps(users, ensure_ascii=False, indent=2))


def get_offset():
    content = get_gist_file("offset_telegram.txt")
    try:
        return int(content.strip()) if content else 0
    except Exception:
        return 0


def save_offset(offset):
    return save_gist_file("offset_telegram.txt", str(offset))


def get_updates(offset=None):
    url = "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/getUpdates"
    params = {"timeout": 10, "limit": 100}
    if offset:
        params["offset"] = offset
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Telegram error:", e)
        return None


async def send_welcome(chat_id, name):
    bot = Bot(token=TELEGRAM_TOKEN)
    msg = "✅ **خوش آمدید " + name + " عزیز!**\n\n"
    msg += "━━━━━━━━━━━━━━━\n\n"
    msg += "شما با موفقیت در سیستم هشدار طوفان ثبت شدید.\n\n"
    msg += "⏳ **حداکثر ۱۰ دقیقه دیگر**، وضعیت آب‌وهوا و هشدارهای طوفان برای شما فعال می‌شود.\n\n"
    msg += "از این به بعد، این پیام‌ها رو خودکار دریافت می‌کنید:\n"
    msg += "🚨 هشدار فوری طوفان\n"
    msg += "🌤️ گزارش آب‌وهوای فردا\n"
    msg += "🌫️ وضعیت گرد و خاک\n\n"
    msg += "━━━━━━━━━━━━━━━\n"
    try:
        await bot.send_message(chat_id=chat_id, text=msg)
        print("Welcome sent to:", chat_id)
        return True
    except Exception as e:
        print("Failed to send welcome:", chat_id, e)
        return False


def collect():
    print("Collecting Telegram Chat IDs")
    users = get_gist_users()
    old_users = dict(users)
    print("Users before:", len(users))

    offset = get_offset()
    print("Offset before:", offset)

    data = get_updates(offset)
    if not data or not data.get("ok"):
        print("Error getting updates")
        return

    updates = data.get("result", [])
    print("Updates received:", len(updates))
    new_users = []
    last_id = offset

    for update in updates:
        last_id = update.get("update_id", last_id)
        message = update.get("message")
        if not message:
            continue
        chat = message.get("chat", {})
        chat_id = str(chat.get("id"))
        name = chat.get("first_name", "") or chat.get("title", "Unknown")
        if chat_id not in users:
            users[chat_id] = name
            new_users.append((chat_id, name))
            print("NEW:", chat_id, "|", name)

    if new_users:
        save_gist_users(users)
        print("Gist updated. Total:", len(users))

        # ارسال پیام خوش‌آمد به نفرات جدید
        for chat_id, name in new_users:
            asyncio.run(send_welcome(chat_id, name))

    if last_id > 0:
        save_offset(last_id + 1)

    print("Total users:", len(users))


if __name__ == "__main__":
    collect()