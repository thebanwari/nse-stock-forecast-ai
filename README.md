# NSE Stock Forecasting (LSTM + Flask)

This project is a simple end-to-end stock forecasting application built for learning and experimentation.  
It predicts the next 5 days of stock prices for NSE-listed companies using an LSTM model and shows a 1-year price chart on the UI.

I built this mainly to understand how LSTM models behave with time-series data and how to integrate ML models inside a real Flask application.

---

## Features

- 5-day stock price prediction using a trained LSTM model  
- 1-year historical price chart (Chart.js)  
- Buy/Sell recommendation based on predicted trend  
- Confidence score using dropout-based sampling  
- Autocomplete search for NSE stocks  
- Simple and clean frontend (HTML, CSS, JS)  
- Model and scaler caching so it doesn't retrain every time  
- Uses Yahoo Finance for live market data  

---

## Tech Stack

**Backend:** Flask (Python)  
**Model:** LSTM (TensorFlow / Keras)  
**Frontend:** HTML, CSS, JavaScript, Chart.js  
**Data:** Yahoo Finance (yfinance)

---

##  Application Screenshot

Below is a full view of the Stock Predictor UI, showing:

- Stock input + autocomplete  
- Prediction results (Buy/Sell, confidence, price change)  
- 5-day forecast  
- 1-year historical + 5-day future chart (Chart.js)

<p align="center">
  <img src="screenshots\app_ui.png" width="900">
</p>

## How to Run

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME
cd YOUR_REPO_NAME


