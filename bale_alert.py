import os
import json
import requests
from jalali import now_jalali


BALE_TOKEN = os.getenv("BALE_TOKEN")
GIST_ID = os.getenv("GIST_ID")
GH_PAT = os.getenv("GH_PAT")


def get_bale_users():
    url = "https://api.github.com/gists/" + GIST_ID
    headers = {"Authorization": "token " + GH_PAT}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        content = r.json()["files"].get("bale_users.json", {}).get("content", "")
        return json.loads(content) if content else {}
    except Exception as e:
        print("Gist error:", e)
        return {}


def send_message(chat_id, text):
    url = "https://tapi.bale.ai/bot" + BALE_TOKEN + "/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=data, timeout=30)
        r.raise_for_status()
        print("  Bale Sent:", chat_id)
        return True
    except Exception as e:
        print("  Bale Failed:", chat_id, e)
        return False


def main():
    print("=" * 60)
    print("تست بله - " + now_jalali())
    print("=" * 60)

    msg = "🧪 **تست بله**\n\n"
    msg += "📅 " + now_jalali() + "\n"
    msg += "━━━━━━━━━━━━━━━\n"
    msg += "اگر این پیام را دیدید، بله کار می‌کند. ✅\n"
    msg += "━━━━━━━━━━━━━━━\n"

    users = get_bale_users()
    print("Bale recipients:", len(users))
    for chat_id in users.keys():
        send_message(chat_id, msg)

    print("Done.")


if __name__ == "__main__":
    main()