import os
import csv
import asyncio
from datetime import datetime
from jalali import now_jalali, to_jalali
from notifier import _send_to_all_async

def get_latest_marine_data():
    filename = "persian_gulf_marine_data.csv"
    if not os.path.exists(filename):
        print(f"File {filename} does not exist.")
        return None
    
    try:
        with open(filename, mode="r", encoding="utf-8") as file:
            reader = csv.reader(file)
            rows = list(reader)
            if len(rows) > 1:
                last_row = rows[-1]
                print(f"Latest marine data found: {last_row}")
                return {
                    "time": last_row[0],
                    "swh": float(last_row[1]) if last_row[1] else 0.0,
                    "sst": last_row[2]
                }
            else:
                print("File is empty or only has header.")
    except Exception as e:
        print("Error reading marine CSV:", e)
    return None

def build_marine_message():
    msg = "🌊 **گزارش داده‌های دریایی خلیج فارس** 🌊\n\n"
    msg += "📅 " + now_jalali() + "\n"
    msg += "━━━━━━━━━━━━━━━\n\n"
    
    marine = get_latest_marine_data()
    if marine:
        time_str = marine['time']
        jalali_time = to_jalali(time_str)
        
        if " - " in jalali_time:
            date_part, time_part = jalali_time.split(" - ")
            msg += "📊 **آخرین داده‌های ثبت شده:**\n\n"
            msg += f"   🗓️ تاریخ ثبت: {date_part}\n"
            msg += f"   🕐 ساعت ثبت: {time_part}\n"
        else:
            msg += f"   🕐 زمان ثبت: {jalali_time}\n"

        msg += f"   🌡️ دمای سطح آب (SST): {marine['sst']} °C\n"
        msg += f"   🌊 ارتفاع موج شاخص (SWH): {marine['swh']} متر\n\n"
        
        if marine['swh'] >= 3.0:
            print("Warning: Wave height is above 3 meters!")
            msg += "🚨 **هشدار دریایی:** ارتفاع موج به بالای ۳ متر رسیده است! طوفان دریایی شدید. لطفاً از تردد با شناورهای سبک خودداری کنید.\n\n"
    else:
        msg += "⚠️ هنوز داده‌ای ثبت نشده است.\n"
        msg += "لطفاً اکشن (Marine Data Collection) را در گیت‌هاب اجرا کنید.\n\n"
        
    msg += "━━━━━━━━━━━━━━━\n"
    return msg

async def main():
    print("=" * 60)
    print("گزارش دریایی - " + now_jalali())
    print("=" * 60)
    
    msg = build_marine_message()
    print("Sending marine report to Bale and Telegram...")
    await _send_to_all_async(msg)
    print("Done. Marine report sent.")

if __name__ == "__main__":
    asyncio.run(main())