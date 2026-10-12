"""
ثبت‌نام خودکار: /startهای جدید را از بله می‌گیرد و در Gist ذخیره می‌کند.
"""
import os
import json
import requests
from config import BALE_TOKEN


GIST_ID = os.getenv("GIST_ID")
GH_PAT = os.getenv("GH_PAT")


def get_gist_users():
    url = "https://api.github.com/gists/" + GIST_ID
    headers = {"Authorization": "token " + GH_PAT}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        content = r.json()["files"]["users.json"]["content"]
        return json.loads(content) if content else {}
    except Exception as e:
        print("Gist read error:", e)
        return {}


def save_gist_users(users):
    url = "https://api.github.com/gists/" + GIST_ID
    headers = {"Authorization": "token " + GH_PAT}
    data = {
        "files": {
            "users.json": {
                "content": json.dumps(users, ensure_ascii=False, indent=2)
            }
        }
    }
    try:
        r = requests.patch(url, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        print("Gist updated. Total users:", len(users))
        return True
    except Exception as e:
        print("Gist write error:", e)
        return False


def get_updates(offset=None):
    url = "https://tapi.bale.ai/bot" + BALE_TOKEN + "/getUpdates"
    params = {"timeout": 10}
    if offset:
        params["offset"] = offset
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Bale getUpdates error:", e)
        return None


def register_new_users():
    print("=" * 60)
    print("ثبت‌نام خودکار کاربران")
    print("=" * 60)

    users = get_gist_users()
    print("Users in Gist:", len(users))

    offset = None
    new_count = 0

    for _ in range(3):
        data = get_updates(offset)
        if not data or not data.get("ok"):
            break

        updates = data.get("result", [])
        if not updates:
            break

        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message")
            if not message:
                continue

            chat = message.get("chat", {})
            chat_id = str(chat.get("id"))
            name = chat.get("first_name", "") + " " + chat.get("last_name", "")
            name = name.strip() or chat.get("title", "Unknown")

            if chat_id not in users:
                users[chat_id] = name
                new_count += 1
                print("NEW:", chat_id, "-", name)

    if new_count > 0:
        save_gist_users(users)
    else:
        print("No new users.")

    print("Total users:", len(users))


if __name__ == "__main__":
    register_new_users()