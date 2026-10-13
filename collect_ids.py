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
    data = {"files": {"users.json": {"content": json.dumps(users, ensure_ascii=False, indent=2)}}}
    try:
        r = requests.patch(url, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        print("Gist updated. Total users:", len(users))
        return True
    except Exception as e:
        print("Gist write error:", e)
        return False


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
    print("Collecting Chat IDs")
    users = get_gist_users()
    print("Users in Gist before:", len(users))

    data = get_all_updates()
    if not data or not data.get("ok"):
        print("Error getting updates")
        return

    updates = data.get("result", [])
    print("Updates received:", len(updates))
    new_count = 0
    last_update_id = 0

    for update in updates:
        last_update_id = update.get("update_id", 0)
        message = update.get("message") or update.get("channel_post")
        if not message:
            continue
        chat = message.get("chat", {})
        chat_id = str(chat.get("id"))
        name = chat.get("first_name", "") or chat.get("title", "Unknown")
        if chat_id not in users:
            users[chat_id] = name
            new_count += 1
            print("NEW:", chat_id, "|", name)

    if new_count > 0:
        save_gist_users(users)
    else:
        print("No new users.")

    # ✅ مهم: offset را ذخیره کن تا پیام‌های تکراری خوانده نشوند
    if last_update_id > 0:
        with open("last_update.txt", "w") as f:
            f.write(str(last_update_id + 1))

    print("Total users in Gist:", len(users))


if __name__ == "__main__":
    collect()