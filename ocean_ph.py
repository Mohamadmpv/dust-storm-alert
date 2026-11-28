from ocean_common import STATIONS, fetch_copernicus_data, get_time_str

async def show_ph_report(callback):
    msg = "🧪 **وضعیت pH در آب‌های ایران**\n\n"
    msg += f"🕐 **ساعت ارزیابی:** {get_time_str()}\n\n"
    for name, (lat, lon) in STATIONS.items():
        val = fetch_copernicus_data("cmems_mod_glo_bgc_my_0.25deg_P1D-m", "ph", lat, lon, days_back=5)
        msg += f"🔹 **{name}:** {val if val else 'نامشخص'}\n"
    await callback.message.edit_text(msg, reply_markup=callback.message.reply_markup)

async def show_oxygen_report(callback):
    msg = "⚖️ **اکسیژن محلول (DO) در آب‌های ایران**\n\n"
    msg += f"🕐 **ساعت ارزیابی:** {get_time_str()}\n\n"
    for name, (lat, lon) in STATIONS.items():
        val = fetch_copernicus_data("cmems_mod_glo_bgc_my_0.25deg_P1D-m", "o2", lat, lon, days_back=5)
        msg += f"🔹 **{name}:** {val if val else 'نامشخص'} mmol/m³\n"
    await callback.message.edit_text(msg, reply_markup=callback.message.reply_markup)