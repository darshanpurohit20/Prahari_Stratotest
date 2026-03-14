# engine/data.py
# Fetches historical OHLCV data from yfinance
# All timeframes supported with honest limitation handling

import yfinance as yf
import pandas as pd
import os
from datetime import datetime, timedelta
from tiingo import TiingoClient
from dotenv import load_dotenv

load_dotenv()

# ── Tiingo Client Setup ───────────────────────────────────────
TIINGO_API_KEY = os.getenv("TIINGO_API_KEY", "")
tiingo_config = {'api_key': TIINGO_API_KEY, 'session': True}
tiingo_client = TiingoClient(tiingo_config)

# ── Timeframe config ──────────────────────────────────────────
TIMEFRAME_CONFIG = {
    "1m": {
        "yf_interval": "1m",
        "max_period":  "7d",
        "display":     "1 Minute",
        "warning":     "⚠️ Only 7 days available for 1min data (yfinance limit)"
    },
    "5m": {
        "yf_interval": "5m",
        "max_period":  "60d",
        "display":     "5 Minutes",
        "warning":     "⚠️ Only 60 days available for 5min data (yfinance limit)"
    },
    "15m": {
        "yf_interval": "15m",
        "max_period":  "60d",
        "display":     "15 Minutes",
        "warning":     "⚠️ Only 60 days available for 15min data (yfinance limit)"
    },
    "30m": {
        "yf_interval": "30m",
        "max_period":  "60d",
        "display":     "30 Minutes",
        "warning":     "⚠️ Only 60 days available for 30min data (yfinance limit)"
    },
    "1h": {
        "yf_interval": "1h",
        "max_period":  "2y",
        "display":     "1 Hour",
        "warning":     None
    },
    "4h": {
        "yf_interval": "1h",       # fetch 1H → resample to 4H
        "max_period":  "2y",
        "display":     "4 Hour",
        "warning":     "ℹ️ 4H candles resampled from 1H data"
    },
    "1d": {
        "yf_interval": "1d",
        "max_period":  "10y",
        "display":     "Daily",
        "warning":     None
    },
    "1wk": {
        "yf_interval": "1wk",
        "max_period":  "20y",
        "display":     "Weekly",
        "warning":     None
    }
}

# ── Period config ─────────────────────────────────────────────
PERIOD_CONFIG = {
    "7d":  "7d",
    "60d": "60d",
    "1y":  "1y",
    "2y":  "2y",
    "3y":  "3y",
    "5y":  "5y",
    "10y": "10y",
}

# ── Period to days mapping ────────────────────────────────────
PERIOD_DAYS = {
    "7d":  7,
    "60d": 60,
    "1y":  365,
    "2y":  730,
    "3y":  1095,
    "5y":  1825,
    "10y": 3650,
    "20y": 7300,
}


# ── Caching Config ───────────────────────────────────────────
CACHE_DIR = os.path.join(os.getcwd(), ".cache", "data")
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_data(ticker: str, timeframe: str, period: str, market: str = "india_equity") -> pd.DataFrame:
    """
    Fetches OHLCV data with smart caching.
    Routes between Tiingo and Yahoo Finance based on detected market.
    """
    config = TIMEFRAME_CONFIG.get(timeframe)
    if not config:
        raise ValueError(f"Unsupported timeframe: {timeframe}. Supported: {list(TIMEFRAME_CONFIG.keys())}")

    # 0. Check Cache
    cache_file = f"{ticker.replace('^', '').replace('=', '')}_{timeframe}_{period}.parquet".lower()
    cache_path = os.path.join(CACHE_DIR, cache_file)
    
    if os.path.exists(cache_path):
        # Cache TTL: 4h for intraday, 24h for daily+
        mtime = datetime.fromtimestamp(os.path.getmtime(cache_path))
        ttl_hours = 4 if "m" in timeframe or "h" in timeframe else 24
        if datetime.now() - mtime < timedelta(hours=ttl_hours):
            print(f"[data.py] Loading {ticker} from cache...")
            return pd.read_parquet(cache_path)

    # 1. Routing Logic: Prioritize Tiingo for non-Indian markets
    df = None
    is_major_crypto = any(c in ticker.upper() for c in ["BTC", "ETH", "USDT", "STETH", "SOL"])
    is_intl_market = market in ("crypto", "forex", "us_equity", "commodity")
    
    if (is_intl_market or is_major_crypto) and TIINGO_API_KEY and TIINGO_API_KEY != "paste_your_tiingo_api_key_here":
        # Try Tiingo for Crypto/US/Forex
        df = _fetch_from_tiingo(ticker, timeframe, period, market)
    
    if df is None or df.empty:
        # 2. Fallback to Yahoo Finance (Always used for india_equity or if Tiingo fails)
        df = _fetch_from_yahoo(ticker, timeframe, period)

    # 3. Save to Cache if successful
    if df is not None and not df.empty:
        df.to_parquet(cache_path)
    
    return df


def _fetch_from_yahoo(ticker: str, timeframe: str, period: str) -> pd.DataFrame:
    config = TIMEFRAME_CONFIG.get(timeframe)
    actual_period = _cap_period(period, config["max_period"])

    try:
        df = yf.download(
            tickers=ticker,
            period=actual_period,
            interval=config["yf_interval"],
            auto_adjust=True,
            progress=False
        )

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(inplace=True)

        if timeframe == "4h":
            df = _resample_to_4h(df)

        return df

    except Exception as e:
        print(f"[data.py] Yahoo Finance failed for {ticker}: {e}")
        return None


def _fetch_from_tiingo(ticker: str, timeframe: str, period: str, market: str) -> pd.DataFrame:
    """Fetch from Tiingo API with proper market-specific ticker normalization"""
    # 1. Normalize Ticker for Tiingo
    t = ticker.upper()
    if market == "crypto":
        t = t.replace("-USD", "usd").replace("-", "").lower()
    elif market == "forex":
        t = t.replace("=X", "").lower()
    else:
        t = t.upper() # Stocks use upper case typically

    # 2. Map timeframe to Tiingo resampleFreq
    resample_map = {
        "1m": "1min", "5m": "5min", "15m": "15min", 
        "30m": "30min", "1h": "1hour", "1d": "daily"
    }
    freq = resample_map.get(timeframe, "1hour")
    
    # 3. Handle periods
    days_map = PERIOD_DAYS.get(period, 730)
    start_date = (datetime.now() - timedelta(days=days_map)).strftime('%Y-%m-%d')
    
    try:
        price_data = []
        if market == "crypto":
             price_data = tiingo_client.get_crypto_price_history(
                tickers=[t], startDate=start_date, resampleFreq=freq
            )
        elif market == "forex":
            price_data = tiingo_client.get_forex_price_history(
                tickers=[t], startDate=start_date, resampleFreq=freq
            )
        else:
            # US Stocks / Commodities
            price_data = tiingo_client.get_ticker_price(
                t, startDate=start_date, resampleFreq=freq
            )

        if not price_data: return None
        
        # Tiingo returns data specifically for the ticker
        # If multiple tickers requested, it's a list of dicts with 'ticker' key
        # If single, it's a list of bars
        if isinstance(price_data, list) and len(price_data) > 0 and 'priceData' in price_data[0]:
            actual_bars = price_data[0]['priceData']
        else:
            actual_bars = price_data

        df = pd.DataFrame(actual_bars)
        if df.empty: return None

        # Clean columns
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # Map Tiingo columns to Prahari columns
        # Tiingo: open, high, low, close, volume (sometimes adjClose)
        rename_map = {
            'open': 'Open', 'high': 'High', 'low': 'Low', 
            'close': 'Close', 'volume': 'Volume'
        }
        df = df.rename(columns=rename_map)
        
        # Ensure only core columns
        valid = ["Open", "High", "Low", "Close", "Volume"]
        df = df[[c for c in valid if c in df.columns]]
        df.dropna(inplace=True)

        print(f"[data.py] Successfully fetched {len(df)} bars from Tiingo for {ticker}")
        return df

    except Exception as e:
        print(f"[data.py] Tiingo failed for {ticker}: {e}")
        return None


def get_warnings(timeframe: str, period: str) -> list:
    """Returns data limitation warnings for this timeframe/period combo"""
    warnings = []
    config = TIMEFRAME_CONFIG.get(timeframe, {})

    if config.get("warning"):
        warnings.append(config["warning"])

    # Warn if period was capped
    max_days = PERIOD_DAYS.get(config.get("max_period", "2y"), 730)
    req_days = PERIOD_DAYS.get(period, 730)
    if req_days > max_days:
        warnings.append(
            f"⚠️ Requested {period} but only {config['max_period']} "
            f"available for {timeframe} timeframe"
        )

    return warnings


def get_available_periods(timeframe: str) -> list:
    """Returns available backtest periods for a given timeframe"""
    config = TIMEFRAME_CONFIG.get(timeframe, {})
    max_period = config.get("max_period", "2y")
    max_days = PERIOD_DAYS.get(max_period, 730)

    available = []
    for period, days in PERIOD_DAYS.items():
        if days <= max_days:
            available.append(period)
    return available


# ── Private helpers ───────────────────────────────────────────

def _resample_to_4h(df: pd.DataFrame) -> pd.DataFrame:
    """Resample 1H candles into 4H candles"""
    df_4h = df.resample("4H").agg({
        "Open":   "first",
        "High":   "max",
        "Low":    "min",
        "Close":  "last",
        "Volume": "sum"
    }).dropna()
    return df_4h


def _cap_period(requested: str, max_available: str) -> str:
    """Cap requested period to what yfinance supports"""
    req_days = PERIOD_DAYS.get(requested, 730)
    max_days = PERIOD_DAYS.get(max_available, 730)
    if req_days > max_days:
        return max_available
    return requested
