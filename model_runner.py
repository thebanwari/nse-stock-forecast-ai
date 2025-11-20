import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def create_dataset(series: pd.Series, window_size: int = 60):
    data = series.values.reshape(-1, 1)
    X, y = [], []
    for i in range(window_size, len(data)):
        X.append(data[i-window_size:i, 0])
        y.append(data[i, 0])
    X = np.array(X)
    y = np.array(y)
    X = X.reshape((X.shape[0], X.shape[1], 1))
    return X, y

def build_model(input_shape):
    model = Sequential()
    model.add(LSTM(100, return_sequences=True, input_shape=input_shape))
    model.add(Dropout(0.2))
    model.add(LSTM(100))
    model.add(Dropout(0.2))
    model.add(Dense(1))
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model

def train_model(series: pd.Series, window_size: int = 60, epochs: int = 12, batch_size: int = 32):
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled = scaler.fit_transform(series.values.reshape(-1, 1))
    scaled_series = pd.Series(scaled.flatten())
    X, y = create_dataset(scaled_series, window_size)
    if len(X) == 0:
        raise ValueError("Not enough data to create training sequences.")
    model = build_model((X.shape[1], 1))
    es = EarlyStopping(monitor='loss', patience=5, restore_best_weights=True)
    model.fit(X, y, epochs=epochs, batch_size=batch_size, callbacks=[es], verbose=1)
    return model, scaler

def predict_future(model, scaler: MinMaxScaler, series: pd.Series, days: int = 5, window_size: int = 60):
    last_window = series.values[-window_size:].reshape(-1, 1)
    scaled_last = scaler.transform(last_window)
    preds = []
    for _ in range(days):
        x_input = scaled_last.reshape((1, window_size, 1))
        p = model.predict(x_input, verbose=0)[0][0]
        preds.append(p)
        scaled_last = np.append(scaled_last[1:], [[p]], axis=0)
    preds = np.array(preds).reshape(-1, 1)
    inv = scaler.inverse_transform(preds).flatten()
    return inv

def mc_dropout_confidence(model, scaler, series: pd.Series, days=5, window_size=60, runs=30):
    preds_all = []
    for r in range(runs):
        try:
            p = predict_future(model, scaler, series, days=days, window_size=window_size)
            preds_all.append(p)
        except Exception:
            continue
    if not preds_all:
        return 0.0
    preds_all = np.array(preds_all) 
    stds = preds_all.std(axis=0)
    last_std = stds[-1]
    mean_last = preds_all.mean(axis=0)[-1]
    if mean_last == 0:
        return 0.0
    normalized = min(max(last_std / abs(mean_last), 0.0), 1.0)
    confidence = max(0.0, min(100.0, 100.0 - normalized * 100.0))
    return float(round(confidence, 2))
