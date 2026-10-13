import asyncio
import os
import json
import requests
from telegram import Bot
from jalali import now_jalali


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GIST_ID = os.getenv("GIST_ID")
GH_PAT = os.getenv("GH_PAT")


def get_all_chat_ids():
    chat_ids = []
    try:
        if GIST_ID and GH_PAT:
            url = "https://api.github.com/gists/" + GIST_ID
            headers = {"Authorization": "token " + GH_PAT}
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            content = r.json()["files"]["users.json"]["content"]
            users = json.loads(content) if content else {}
            for cid in users.keys():
                cid = str(cid).strip()
                if cid and cid not in chat_ids:
                    chat_ids.append(cid)
    except Exception as e:
        print("Gist read error:", e)
    return chat_ids


async def send_to_all(message):
    bot = Bot(token=TELEGRAM_TOKEN)
    chat_ids = get_all_chat_ids()
    print("Total recipients:", len(chat_ids))
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
            print("Sent to:", chat_id)
        except Exception as e:
            print("Failed:", chat_id, e)


if __name__ == "__main__":
    msg = "🧪 تست ربات تلگرام\n\n📅 " + now_jalali()
    asyncio.run(send_to_all(msg))