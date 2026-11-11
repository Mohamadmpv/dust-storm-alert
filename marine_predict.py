import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime, timedelta
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler

# مختصات خلیج فارس
LAT = 27.1832
LON = 56.2666
LOOK_BACK = 24

def fetch_latest_data():
    """دریافت داده‌های جدید از API"""
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": LAT, "longitude": LON,
        "hourly": "wave_height,sea_surface_temperature",
        "forecast_days": 2, "timezone": "Asia/Tehran"
    }
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    return r.json()

def predict_marine():
    print("Fetching latest marine data for prediction...")
    data = fetch_latest_data()
    
    if not data or "hourly" not in data:
        return None

    hourly = data["hourly"]
    # ساخت دیتافریم از داده‌های جدید
    df = pd.DataFrame({
        "SWH (m)": hourly["wave_height"],
        "SST (C)": hourly["sea_surface_temperature"]
    }).dropna()

    if len(df) < LOOK_BACK:
        print("Not enough data for prediction.")
        return None

    # بارگذاری اسکیلر (برای سادگی از مینیمم و ماکسیمم داده‌های جدید استفاده می‌کنیم)
    scaler = MinMaxScaler()
    scaler.fit(df[["SWH (m)", "SST (C)"]])
    scaled_data = scaler.transform(df[["SWH (m)", "SST (C)"]])

    # گرفتن آخرین ۲۴ ساعت به عنوان ورودی
    last_24h = scaled_data[-LOOK_BACK:].reshape(1, LOOK_BACK, 2)

    try:
        # بارگذاری مدل‌ها
        model_swh = load_model('model_gru_swh.h5')
        model_sst = load_model('model_gru_sst.h5')

        # پیش‌بینی
        pred_swh_scaled = model_swh.predict(last_24h, verbose=0)[0][0]
        pred_sst_scaled = model_sst.predict(last_24h, verbose=0)[0][0]

        # برگرداندن به مقیاس اصلی
        # چون اسکیلر روی دو ستون فیت شده، باید یک آرایه دو بعدی بسازیم
        dummy = np.array([[pred_swh_scaled, pred_sst_scaled]])
        pred_inv = scaler.inverse_transform(dummy)
        
        predicted_swh = round(pred_inv[0][0], 2)
        predicted_sst = round(pred_inv[0][1], 2)

        print(f"Predicted SWH for next 24h: {predicted_swh} meters")
        print(f"Predicted SST for next 24h: {predicted_sst} °C")
        
        return {
            "swh": predicted_swh,
            "sst": predicted_sst,
            "time": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        }

    except Exception as e:
        print(f"Error in prediction: {e}")
        return None

if __name__ == "__main__":
    result = predict_marine()
    if result:
        print(f"\n✅ Prediction for {result['time']}:")
        print(f"   🌊 Wave Height: {result['swh']} m")
        print(f"   🌡️ Sea Temperature: {result['sst']} °C")