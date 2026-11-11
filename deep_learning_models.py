import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, GRU, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping

def load_and_prepare_data(filepath="persian_gulf_marine_data.csv", look_back=24):
    """بارگذاری داده‌ها و آماده‌سازی برای مدل‌های سری زمانی"""
    df = pd.read_csv(filepath)
    df['DateTime'] = pd.to_datetime(df['DateTime'])
    df = df.sort_values('DateTime').reset_index(drop=True)
    
    # پر کردن مقادیر خالی
    df['SWH (m)'] = df['SWH (m)'].interpolate()
    df['SST (C)'] = df['SST (C)'].interpolate()
    
    # نرمال‌سازی داده‌ها
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(df[['SWH (m)', 'SST (C)']])
    
    X, y_swh, y_sst = [], [], []
    for i in range(len(scaled_data) - look_back):
        X.append(scaled_data[i:i+look_back])
        y_swh.append(scaled_data[i+look_back, 0]) # SWH
        y_sst.append(scaled_data[i+look_back, 1]) # SST
    
    X = np.array(X)
    y_swh = np.array(y_swh)
    y_sst = np.array(y_sst)
    
    # تقسیم به آموزش و تست
    split = int(len(X) * 0.8)
    return X[:split], X[split:], y_swh[:split], y_swh[split:], y_sst[:split], y_sst[split:], scaler

def build_lstm_model(input_shape):
    """ساخت مدل LSTM"""
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(32),
        Dropout(0.2),
        Dense(16, activation='relu'),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    return model

def build_gru_model(input_shape):
    """ساخت مدل GRU-DNN"""
    model = Sequential([
        GRU(64, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        GRU(32),
        Dense(16, activation='relu'),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    return model

def train_models():
    print("Loading data...")
    X_train, X_test, y_swh_train, y_swh_test, y_sst_train, y_sst_test, scaler = load_and_prepare_data()
    
    input_shape = (X_train.shape[1], X_train.shape[2])
    print(f"Input shape: {input_shape}")
    
    early_stop = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
    
    # --- آموزش LSTM برای SWH ---
    print("\n--- Training LSTM for SWH ---")
    lstm_swh = build_lstm_model(input_shape)
    lstm_swh.fit(X_train, y_swh_train, epochs=20, batch_size=32, validation_split=0.1, callbacks=[early_stop], verbose=1)
    lstm_swh_loss = lstm_swh.evaluate(X_test, y_swh_test)
    print(f"LSTM SWH Loss: {lstm_swh_loss}")
    
    # --- آموزش GRU-DNN برای SWH ---
    print("\n--- Training GRU-DNN for SWH ---")
    gru_swh = build_gru_model(input_shape)
    gru_swh.fit(X_train, y_swh_train, epochs=20, batch_size=32, validation_split=0.1, callbacks=[early_stop], verbose=1)
    gru_swh_loss = gru_swh.evaluate(X_test, y_swh_test)
    print(f"GRU-DNN SWH Loss: {gru_swh_loss}")
    
    # --- آموزش LSTM برای SST ---
    print("\n--- Training LSTM for SST ---")
    lstm_sst = build_lstm_model(input_shape)
    lstm_sst.fit(X_train, y_sst_train, epochs=20, batch_size=32, validation_split=0.1, callbacks=[early_stop], verbose=1)
    lstm_sst_loss = lstm_sst.evaluate(X_test, y_sst_test)
    print(f"LSTM SST Loss: {lstm_sst_loss}")
    
    # --- آموزش GRU-DNN برای SST ---
    print("\n--- Training GRU-DNN for SST ---")
    gru_sst = build_gru_model(input_shape)
    gru_sst.fit(X_train, y_sst_train, epochs=20, batch_size=32, validation_split=0.1, callbacks=[early_stop], verbose=1)
    gru_sst_loss = gru_sst.evaluate(X_test, y_sst_test)
    print(f"GRU-DNN SST Loss: {gru_sst_loss}")
    
    print("\nModels trained successfully!")

if __name__ == "__main__":
    train_models()