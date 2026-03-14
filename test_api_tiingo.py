import requests
import json

url = "http://localhost:8000/api/v1/backtest"
payload = {
    "user_input": "Bitcoin RSI below 30 buy",
    "ticker": "AUTO",
    "timeframe": "1h",
    "period": "60d",
    "initial_capital": 100000,
    "market": "crypto"
}

try:
    print(f"Sending request to {url}...")
    response = requests.post(url, json=payload, timeout=60)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Strategy: {data['strategy_name']}")
        print(f"Ticker: {data['ticker']}")
        print(f"Metrics: {json.dumps(data['metrics'], indent=2)}")
        if "Successfully fetched" in str(data.get("notes", "")):
             print("SUCCESS: Tiingo data detected in notes.")
    else:
        print(f"Error Detail: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
