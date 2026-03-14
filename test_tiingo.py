import os
import pandas as pd
from tiingo import TiingoClient
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

TIINGO_API_KEY = os.getenv("TIINGO_API_KEY", "")
print(f"Using Tiingo API Key: {TIINGO_API_KEY[:5]}...")

tiingo_config = {'api_key': TIINGO_API_KEY, 'session': True}
client = TiingoClient(tiingo_config)

def test_crypto():
    print("\n--- Testing Crypto (BTCUSD) ---")
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    try:
        data = client.get_crypto_price_history(
            tickers=['btcusd'], startDate=start_date, resampleFreq='1hour'
        )
        if data and len(data) > 0:
            print(f"Success! Received {len(data[0]['priceData'])} bars for btcusd.")
            df = pd.DataFrame(data[0]['priceData'])
            print(df.head(2))
        else:
            print("Failed: No data received for btcusd.")
    except Exception as e:
        print(f"Error: {e}")

def test_equity():
    print("\n--- Testing US Equity (AAPL) ---")
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    try:
        data = client.get_ticker_price(
            "AAPL", startDate=start_date, resampleFreq='daily'
        )
        if data:
            print(f"Success! Received {len(data)} bars for AAPL.")
            df = pd.DataFrame(data)
            print(df.head(2))
        else:
            print("Failed: No data received for AAPL.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_crypto()
    test_equity()
