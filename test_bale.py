import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

import os
BALE_TOKEN = os.getenv("BALE_TOKEN")

logging.basicConfig(level=logging.INFO)

async def main():
    from baleio import Bot, Dispatcher
    from baleio.client.default import DefaultBotProperties
    from baleio.enums import ParseMode
    from baleio.types import Message

    bot = Bot(
        token=BALE_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )

    me = await bot.get_me()
    print("=" * 60)
    print(f"✅ ربات متصل شد: @{me.username}")
    print("=" * 60)
    print("📩 حالا در بله به ربات پیام بفرستید (مثلاً «سلام»).")
    print("=" * 60)

    dp = Dispatcher()

    @dp.message()
    async def on_message(message: Message):
        print()
        print("★" * 60)
        print(f"📬 پیام دریافت شد!")
        print(f"👤 نام: {message.from_user.full_name}")
        print(f"🆔 Chat ID: {message.chat.id}")
        print(f"🆔 User ID: {message.from_user.id}")
        print("★" * 60)
        print()
        print("⬆️ این عدد (Chat ID) را دقیقاً کپی کنید و در فایل .env بگذارید.")
        print()
        await message.answer(f"✅ Chat ID شما: {message.chat.id}")
        await dp.stop_polling()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())