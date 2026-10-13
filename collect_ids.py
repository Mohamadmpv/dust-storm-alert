import os
import json
import requests
from config import BALE_TOKEN

GIST_ID = os.getenv("GIST_ID")
GH_PAT = os.getenv("GH_PAT")


def get_gist_file(filename):
    url = "https://api.github.com/gists/" + GIST_ID
    headers = {"Authorization": "token " + GH_PAT}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        content = r.json()["files"].get(filename, {}).get("content", "")
        return content
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
    content = json.dumps(users, ensure_ascii=False, indent=2)
    return save_gist_file("users.json", content)


def get_offset():
    content = get_gist_file("offset.txt")
    try:
        return int(content.strip()) if content else 0
    except Exception:
        return 0


def save_offset(offset):
    return save_gist_file("offset.txt", str(offset))


def get_all_updates(offset=None):
    url = "https://tapi.bale.ai/bot" + BALE_TOKEN + "/getUpdates"
    params = {"timeout": 10, "limit": 100}
    if offset:
        params["offset"] = offset
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

    offset = get_offset()
    print("Offset before:", offset)

    data = get_all_updates(offset)
    if not data or not data.get("ok"):
        print("Error getting updates")
        return

    updates = data.get("result", [])
    print("Updates received:", len(updates))
    new_count = 0
    last_update_id = offset

    for update in updates:
        last_update_id = update.get("update_id", last_update_id)
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
        print("Gist updated. Total users:", len(users))
    else:
        print("No new users.")

    if last_update_id > 0:
        save_offset(last_update_id + 1)
        print("Offset saved:", last_update_id + 1)

    print("Total users in Gist:", len(users))


if __name__ == "__main__":
    collect()