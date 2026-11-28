import copernicusmarine
from datetime import datetime, timedelta

# ... (مختصات ایستگاه‌ها)

def get_chlorophyll_for_station(lat, lon):
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=3) # داده‌های ماهواره‌ای کمی تاخیر دارند
        ds = copernicusmarine.open_dataset(
            dataset_id="cmems_obs-oc_glo_bgc-plankton_my_l4-gapfree-multi-4km_P1D",
            variables=["CHL"],
            # ... (بقیه تنظیمات)
        )
        if ds["CHL"].size > 0:
            chl_value = float(ds["CHL"].mean())
            return round(chl_value, 2)
    except: pass
    return None

async def show_chlorophyll_report(callback):
    msg = "🟢 **کلروفیل-a (داده ماهواره‌ای) در آب‌های ایران**\n\n"
    msg += f"🕐 **ساعت ارزیابی:** {datetime.now().strftime('%Y/%m/%d - %H:%M')}\n"
    msg += "📡 **منبع:** ماهواره (Sentinel-3/MODIS)\n\n"
    for name, (lat, lon) in STATIONS.items():
        chl = get_chlorophyll_for_station(lat, lon)
        msg += f"🔹 **{name}:** {chl if chl else 'نامشخص'} mg/m³\n"
    await callback.message.edit_text(msg)