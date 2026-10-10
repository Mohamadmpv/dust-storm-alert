from api_client import get_wind_data, get_dust_data

lat, lon = 33.3152, 44.3661

print("دریافت داده باد...")
wind = get_wind_data(lat, lon)

if wind:
    print("داده باد دریافت شد.")
    print(f"مختصات: {wind['latitude']}, {wind['longitude']}")
    print("پیش‌بینی ۵ ساعت اول:")
    print("-" * 50)
    for i in range(5):
        time = wind["hourly"]["time"][i]
        speed = wind["hourly"]["wind_speed_10m"][i]
        direction = wind["hourly"]["wind_direction_10m"][i]
        gust = wind["hourly"]["wind_gusts_10m"][i]
        print(f"{time} | سرعت: {speed} km/h | جهت: {direction} | وزش: {gust} km/h")

print()
print("دریافت داده گرد و خاک...")
dust = get_dust_data(lat, lon)

if dust:
    print("داده گرد و خاک دریافت شد.")
    if "hourly" in dust and "dust" in dust["hourly"]:
        print("غلظت گرد و خاک (۵ ساعت اول):")
        print("-" * 50)
        for i in range(5):
            time = dust["hourly"]["time"][i]
            d = dust["hourly"]["dust"][i]
            pm10 = dust["hourly"]["pm10"][i] if "pm10" in dust["hourly"] else None
            print(f"{time} | dust: {d} | PM10: {pm10}")