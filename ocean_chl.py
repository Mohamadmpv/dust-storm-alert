from ocean_common import STATIONS, fetch_copernicus_data, get_time_str

async def show_chl_report(callback):
    msg = "🟢 **کلروفیل-a (داده ماهواره‌ای)**\n\n"
    msg += f"🕐 **ساعت ارزیابی:** {get_time_str()}\n"
    msg += "📡 **منبع:** Sentinel-3/MODIS\n\n"
    for name, (lat, lon) in STATIONS.items():
        val = fetch_copernicus_data("cmems_obs-oc_glo_bgc-plankton_my_l4-gapfree-multi-4km_P1D", "CHL", lat, lon, days_back=3)
        msg += f"🔹 **{name}:** {val if val else 'نامشخص'} mg/m³\n"
    await callback.message.edit_text(msg, reply_markup=callback.message.reply_markup)