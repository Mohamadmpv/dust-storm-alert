import asyncio
from notifier import _send_to_all
from jalali import now_jalali


async def main():
    msg = "🧪 **پیام تست از GitHub**\n\n"
    msg += "📅 " + now_jalali() + "\n"
    msg += "━━━━━━━━━━━━━━━\n\n"
    msg += "این یک پیام تست است تا مطمئن شویم همه دریافت می‌کنند.\n\n"
    msg += "اگر این پیام را دیدید، یعنی سیستم درست کار می‌کند. ✅\n\n"
    msg += "━━━━━━━━━━━━━━━\n"

    print("Sending test message to all recipients...")
    await _send_to_all(msg)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())