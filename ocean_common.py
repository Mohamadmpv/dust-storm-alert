import os
import copernicusmarine
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
COPERNICUS_USER = os.getenv("COPERNICUS_USER")
COPERNICUS_PASS = os.getenv("COPERNICUS_PASS")

STATIONS = {
    "خلیج فارس (بندرعباس)": (27.18, 56.26),
    "دریای عمان (چابهار)": (25.29, 60.64),
    "دریای خزر (بندر انزلی)": (37.47, 49.46)
}

def get_time_str():
    return datetime.now().strftime('%Y/%m/%d - %H:%M')

def fetch_copernicus_data(dataset_id, variable, lat, lon, days_back=1):
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days_back)
        ds = copernicusmarine.open_dataset(
            dataset_id=dataset_id,
            variables=[variable],
            minimum_longitude=lon - 0.5, maximum_longitude=lon + 0.5,
            minimum_latitude=lat - 0.5, maximum_latitude=lat + 0.5,
            start_datetime=start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            end_datetime=end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            minimum_depth=0, maximum_depth=1.5,
            username=COPERNICUS_USER, password=COPERNICUS_PASS
        )
        if ds[variable].size > 0:
            return round(float(ds[variable].mean()), 2)
    except Exception as e:
        print(f"Copernicus Error ({variable}) for {lat},{lon}: {e}")
    return None