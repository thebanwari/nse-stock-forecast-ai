import requests
import pandas as pd
import time
import logging
import re
from typing import Tuple, Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=max&interval=1d"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

VALID_SYMBOL_RE = re.compile(r"^[A-Za-z0-9\-\._]{1,12}$")


def _call_yahoo_json(ticker: str, retries: int = 3, timeout: int = 8) -> Optional[dict]:
    url = YAHOO_URL.format(ticker=ticker)
    for attempt in range(1, retries + 1):
        try:
            logger.debug(f"Attempt {attempt} fetching {ticker} from Yahoo JSON API")
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            if resp.status_code != 200:
                logger.warning(f"Yahoo returned status {resp.status_code} for {ticker}")
                time.sleep(0.5 * attempt)
                continue
            data = resp.json()
            return data
        except requests.exceptions.RequestException as e:
            logger.warning(f"RequestException for {ticker} attempt {attempt}: {e}")
            time.sleep(0.5 * attempt)
        except ValueError as e:
            logger.warning(f"JSON decode error for {ticker} attempt {attempt}: {e}")
            time.sleep(0.5 * attempt)
    return None


def _parse_yahoo_json(json_data: dict) -> Optional[pd.DataFrame]:
    try:
        chart = json_data.get("chart", {})
        result = chart.get("result")
        if not result:
            return None
        result = result[0]
        timestamps = result.get("timestamp")
        indicators = result.get("indicators", {})
        quote = indicators.get("quote")
        if not timestamps or not quote:
            return None
        closes = quote[0].get("close")
        if not closes:
            return None

        df = pd.DataFrame({"timestamp": timestamps, "Close": closes})
        df.dropna(inplace=True)
        if df.empty:
            return None
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        df.set_index("timestamp", inplace=True)
        df = df.sort_index()
        return df
    except Exception as e:
        logger.exception("Error parsing yahoo json")
        return None


def fetch_stock(symbol: str, min_rows: int = 120) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Attempts to fetch stock data for symbol using a set of possible tickers.
    Returns (df, working_ticker) or (None, None).
    """
    if not symbol or not isinstance(symbol, str):
        logger.warning("Invalid symbol input")
        return None, None

    symbol = symbol.strip().upper()
    symbol = re.sub(r"\.(NS|BO)$", "", symbol)

    if not VALID_SYMBOL_RE.match(symbol):
        logger.warning(f"Symbol '{symbol}' failed validation regex")
        return None, None

    candidates = [f"{symbol}.NS", f"{symbol}.BO", symbol]
    logger.info(f"Trying candidates for {symbol}: {candidates}")

    for ticker in candidates:
        logger.info(f"Trying ticker: {ticker}")
        json_data = _call_yahoo_json(ticker)
        if not json_data:
            logger.info(f"No JSON data for {ticker}")
            continue

        df = _parse_yahoo_json(json_data)
        if df is None:
            logger.info(f"Parsing returned no dataframe for {ticker}")
            continue

        if len(df) < min_rows:
            logger.info(f"Ticker {ticker} returned only {len(df)} rows (< min_rows={min_rows}); skipping")
            continue

        logger.info(f"Success: {ticker} returned {len(df)} rows")
        return df, ticker

    logger.error(f"No valid data found for symbol: {symbol}")
    return None, None
