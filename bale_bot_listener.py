import asyncio
import logging
import sys
import os
from baleio import Bot, Dispatcher, md
from baleio.client.default import DefaultBotProperties
from baleio.enums import ParseMode
from baleio.types import Message
from dotenv import load_dotenv

# وارد کردن تابع پیش‌بینی
from marine_predict import predict_marine

load_dotenv()

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

BALE_TOKEN = os.getenv("BALE_TOKEN")

async def main():
    print("=" * 60)
    print("ربات بله (هشدار و پیش‌بینی) در حال اجراست...")
    print("=" * 60)

    bot = Bot(token=BALE_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    me = await bot.get_me()
    print(f"Bot @{me.username} is listening...")

    dp = Dispatcher()

    @dp.message()
    async def on_message(message: Message):
        text = (message.text or "").lower()
        
        # اگر کاربر درخواست پیش‌بینی دریا کرد
        if "پیش‌بینی" in text or "دریا" in text:
            await message.answer("⏳ در حال تحلیل داده‌ها با هوش مصنوعی... (چند لحظه صبر کنید)")
            result = predict_marine()
            
            if result:
                msg = f"🤖 **پیش‌بینی هوش مصنوعی برای خلیج فارس ({result['time']}):**\n\n"
                msg += f"🌊 ارتفاع موج: {result['swh']} متر\n"
                msg += f"🌡️ دمای آب: {result['sst']} درجه سانتی‌گراد\n\n"
                msg += "📌 این پیش‌بینی با استفاده از مدل GRU-DNN انجام شده است."
                await message.answer(msg)
            else:
                await message.answer("❌ متاسفانه در حال حاضر امکان پیش‌بینی وجود ندارد.")
        else:
            # منوی راهنما
            await message.answer("سلام! برای دریافت پیش‌بینی وضعیت دریا کلمه «پیش‌بینی دریا» را بفرستید.")

    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())