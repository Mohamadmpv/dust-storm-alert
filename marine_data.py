import os
import requests
import csv
from datetime import datetime
from jalali import now_jalali

# مختصات خلیج فارس (نزدیک بندرعباس)
LAT = 27.1832
LON = 56.2666

def fetch_marine_data():
    print("Fetching marine data for Persian Gulf...")
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": "wave_height,sea_surface_temperature",
        "timezone": "Asia/Tehran"
    }
    
    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Error fetching marine data:", e)
        return None

def save_to_csv(data):
    if not data or "hourly" not in data:
        print("No data to save.")
        return
    
    hourly = data["hourly"]
    times = hourly["time"]
    waves = hourly["wave_height"]
    ssts = hourly["sea_surface_temperature"]
    
    filename = "persian_gulf_marine_data.csv"
    file_exists = os.path.isfile(filename)
    
    new_rows = 0
    with open(filename, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["DateTime", "SWH (m)", "SST (C)"])
            
        for i, t in enumerate(times):
            try:
                # فقط داده‌های ساعت‌های آینده را ذخیره می‌کنیم تا از تکرار جلوگیری شود
                dt = datetime.fromisoformat(t)
                if dt > datetime.now():
                    writer.writerow([t, waves[i], ssts[i]])
                    new_rows += 1
            except Exception:
                continue
                
    print(f"Saved {new_rows} new rows to {filename}")

def main():
    print("=" * 60)
    print("Marine Data Collection - " + now_jalali())
    print("=" * 60)
    
    data = fetch_marine_data()
    if data:
        save_to_csv(data)
    print("Done.")

if __name__ == "__main__":
    main()