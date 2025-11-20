import os
import logging
import time
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from data_utils import fetch_stock
from model_runner import train_model, predict_future, mc_dropout_confidence
from cache_utils import model_path_for, scaler_path_for, is_model_recent
from tensorflow.keras.models import load_model
import joblib
import numpy as np
import pandas as pd

WINDOW = 60
EPOCHS = 12
HISTORY_DAYS = 365  # last 1 year for chart

# logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("stockpredictor")

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/history", methods=["GET"])
def history():
    """
    Return last 1-year historical OHLC (we only use 'Close') for charting.
    Response:
    {
      "symbol": "TCS",
      "working_ticker": "TCS.NS",
      "dates": ["2024-11-14", ...],
      "prices": [3120.45, ...]
    }
    """
    symbol = request.args.get("symbol", "").strip()
    if not symbol:
        return jsonify({"error": "provide symbol param, e.g. ?symbol=TCS"}), 400

    logger.info("History request for %s", symbol)
    df, working = fetch_stock(symbol, min_rows=60)  # fetch_stock returns full df if available
    if df is None:
        logger.warning("No data for history %s", symbol)
        return jsonify({"error": f"No history found for {symbol}"}), 404

    # limit to last HISTORY_DAYS days by datetime index
    try:
        # prefer last N days using .last with days string if index is datetime
        last = df.last(f"{HISTORY_DAYS}D")
        # if not enough rows, fallback to taking last 252 rows
        if last.shape[0] < 60:
            last = df.tail(252)
    except Exception:
        last = df.tail(252)

    dates = [d.strftime("%Y-%m-%d") for d in last.index]
    prices = [float(p) for p in last["Close"].tolist()]

    return jsonify({
        "symbol": symbol.upper(),
        "working_ticker": working,
        "dates": dates,
        "prices": prices
    })


@app.route("/predict", methods=["GET"])
def predict():
    """
    Predict endpoint (keeps behavior you already use).
    Returns prediction (5-day list) and recommendation + confidence.
    Does NOT return large history (chart uses /history).
    """
    symbol = request.args.get("symbol", "").strip()
    if not symbol:
        return jsonify({"error": "provide symbol param, e.g. ?symbol=TCS"}), 400

    logger.info("Processing prediction request for %s", symbol)
    df, working = fetch_stock(symbol)
    if df is None:
        logger.warning("No data available for %s", symbol)
        return jsonify({"error": f"No data found for {symbol}"}), 404

    # use working ticker for filenames
    model_file = model_path_for(working)
    scaler_file = scaler_path_for(working)

    model = None
    scaler = None

    try:
        if os.path.exists(model_file) and os.path.exists(scaler_file) and is_model_recent(working):
            logger.info("Loading cached model for %s", working)
            model = load_model(model_file)
            scaler = joblib.load(scaler_file)
        else:
            logger.info("Training new model for %s", working)
            # train on full df['Close'] but model uses WINDOW internally
            model, scaler = train_model(df["Close"], window_size=WINDOW, epochs=EPOCHS)
            model.save(model_file)
            joblib.dump(scaler, scaler_file)
            logger.info("Saved model and scaler for %s", working)
    except Exception as e:
        logger.exception("Model training/loading error")
        return jsonify({"error": "Model training/loading failed", "details": str(e)}), 500

    try:
        # IMPORTANT: prediction uses last WINDOW values internally (model_runner.predict_future)
        preds = predict_future(model, scaler, df["Close"], days=5, window_size=WINDOW)
        confidence = mc_dropout_confidence(model, scaler, df["Close"], days=5, window_size=WINDOW, runs=10)
        rec = "BUY (Uptrend)" if preds[-1] > preds[0] else "SELL (Downtrend)"
        pct = ((preds[-1] - preds[0]) / preds[0]) * 100.0 if preds[0] != 0 else 0.0

        # return numbers rounded as your UI expects
        return jsonify({
            "symbol": symbol.upper(),
            "working_ticker": working,
            "predicted_prices": [round(float(p), 2) for p in preds.tolist()],
            "recommendation": rec,
            "pct_change_%": round(float(pct), 2),
            "confidence": round(float(confidence), 2)
        })
    except Exception as e:
        logger.exception("Prediction error")
        return jsonify({"error": "Prediction failed", "details": str(e)}), 500


if __name__ == "__main__":
    # ensure models_cache exists
    from cache_utils import CACHE_DIR
    os.makedirs(CACHE_DIR, exist_ok=True)
    app.run(debug=True, host="127.0.0.1", port=5000)