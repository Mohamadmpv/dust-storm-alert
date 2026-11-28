import copernicusmarine
from datetime import datetime, timedelta

# ... (مختصات ایستگاه‌ها مثل بالا)

def get_oxygen_for_station(lat, lon):
    try:
        # ... (تنظیمات تاریخ مثل بالا)
        ds = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_bgc_my_0.25deg_P1D-m",
            variables=["o2"], # پارامتر اکسیژن
            # ... (بقیه تنظیمات)
        )
        if ds["o2"].size > 0:
            o2_value = float(ds["o2"].mean())
            return round(o2_value, 2) # میلی‌مول بر متر مکعب
    except: pass
    return None

async def show_oxygen_report(callback):
    msg = "⚖️ **اکسیژن محلول (DO) در آب‌های ایران**\n\n"
    msg += f"🕐 **ساعت ارزیابی:** {datetime.now().strftime('%Y/%m/%d - %H:%M')}\n\n"
    for name, (lat, lon) in STATIONS.items():
        o2 = get_oxygen_for_station(lat, lon)
        msg += f"🔹 **{name}:** {o2 if o2 else 'نامشخص'} mmol/m³\n"
    await callback.message.edit_text(msg)