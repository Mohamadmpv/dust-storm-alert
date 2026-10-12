import os
import requests
from config import BALE_TOKEN


def get_all_updates():
    url = "https://tapi.bale.ai/bot" + BALE_TOKEN + "/getUpdates"
    params = {"timeout": 10, "limit": 100}
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Error:", e)
        return None


def collect():
    print("=" * 60)
    print("جمع‌آوری Chat IDها")
    print("=" * 60)

    data = get_all_updates()
    if not data or not data.get("ok"):
        print("خطا در دریافت اطلاعات")
        return

    updates = data.get("result", [])
    print("تعداد پیام‌های دریافتی:", len(updates))

    chat_ids = []

    for update in updates:
        message = update.get("message") or update.get("channel_post")
        if not message:
            continue

        chat = message.get("chat", {})
        chat_id = str(chat.get("id"))
        chat_type = chat.get("type", "")
        name = chat.get("first_name", "") or chat.get("title", "Unknown")

        if chat_id not in chat_ids:
            chat_ids.append(chat_id)
            print("FOUND:", chat_id, "|", chat_type, "|", name)

    print()
    print("=" * 60)
    print("Chat IDs (کپی کنید):")
    print(",".join(chat_ids))
    print("=" * 60)


if __name__ == "__main__":
    collect()