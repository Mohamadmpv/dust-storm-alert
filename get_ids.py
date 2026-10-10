import asyncio
import logging
import json
import os
from baleio import Bot, Dispatcher
from baleio.client.default import DefaultBotProperties
from baleio.enums import ParseMode
from baleio.types import Message
from config import BALE_TOKEN

logging.basicConfig(level=logging.INFO)

USERS_FILE = "users.json"


def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


async def main():
    bot = Bot(
        token=BALE_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    me = await bot.get_me()
    print("=" * 60)
    print("Bot: @" + me.username)
    print("Ask your friends to send /start to the bot.")
    print("Their Chat IDs will be saved in users.json automatically.")
    print("=" * 60)

    dp = Dispatcher()

    @dp.message()
    async def on_message(message: Message):
        users = load_users()
        chat_id = str(message.chat.id)
        name = message.from_user.full_name

        if chat_id not in users:
            users[chat_id] = name
            save_users(users)
            print()
            print("=" * 60)
            print("NEW USER REGISTERED")
            print("Name: " + name)
            print("Chat ID: " + chat_id)
            print("Total users: " + str(len(users)))
            print("=" * 60)

            await message.answer("✅ شما ثبت شدید! از این پس هشدارهای طوفان را دریافت می‌کنید.")
        else:
            await message.answer("شما قبلاً ثبت شده‌اید.")


    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())