import os
import copernicusmarine
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

COPERNICUS_USER = os.getenv("COPERNICUS_USER")
COPERNICUS_PASS = os.getenv("COPERNICUS_PASS")

def get_copernicus_sst(lat, lon):
    """دریافت دمای سطح آب از Copernicus"""
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        
        ds = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m",
            variables=["thetao"],
            minimum_longitude=lon - 0.1, maximum_longitude=lon + 0.1,
            minimum_latitude=lat - 0.1, maximum_latitude=lat + 0.1,
            start_datetime=start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            end_datetime=end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            minimum_depth=0, maximum_depth=1,
            username=COPERNICUS_USER, password=COPERNICUS_PASS
        )
        sst = float(ds["thetao"].mean())
        return round(sst, 1)
    except Exception as e:
        print(f"Copernicus SST Error for {lat},{lon}: {e}")
        return None

def get_copernicus_chlorophyll(lat, lon):
    """دریافت کلروفیل-a از Copernicus"""
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        
        # استفاده از دیتاست BGC با تفکیک 0.25 درجه (مناسب برای کلروفیل)
        ds = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_bgc_anfc_0.25deg_P1D-m", 
            variables=["chl"],
            minimum_longitude=lon - 0.5, maximum_longitude=lon + 0.5,
            minimum_latitude=lat - 0.5, maximum_latitude=lat + 0.5,
            start_datetime=start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            end_datetime=end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            minimum_depth=0, maximum_depth=1,
            username=COPERNICUS_USER, password=COPERNICUS_PASS
        )
        chl = float(ds["chl"].mean())
        return round(chl, 2)
    except Exception as e:
        print(f"Copernicus Chl Error for {lat},{lon}: {e}")
        return None