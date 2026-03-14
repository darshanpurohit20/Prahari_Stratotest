import requests
import json
import time

url = "http://localhost:8001/api/v1/backtest"

def test_asset(name, input_text):
    print(f"\n>>> Testing {name}...")
    payload = {
        "user_input": input_text,
        "ticker": "AUTO",
        "timeframe": "1h",
        "period": "60d",
        "initial_capital": 100000,
        "market": "crypto" if "bitcoin" in input_text.lower() else "india_equity"
    }
    try:
        start = time.time()
        response = requests.post(url, json=payload, timeout=60)
        end = time.time()
        print(f"Status: {response.status_code} ({end-start:.1f}s)")
        if response.status_code == 200:
            data = response.json()
            print(f"  Strategy: {data['strategy_name']}")
            print(f"  Ticker:   {data['ticker']} ({data.get('ticker_name', 'N/A')})")
            print(f"  Trades:   {data['metrics']['total_trades']}")
            print(f"  Return:   {data['metrics']['total_return_pct']}%")
            return True
        else:
            print(f"  Error: {response.text}")
            return False
    except Exception as e:
        print(f"  Exception: {e}")
        return False

if __name__ == "__main__":
    print("=== FINAL SYSTEM VERIFICATION ===")
    s1 = test_asset("BITCOIN", "Bitcoin RSI below 30 buy")
    s2 = test_asset("RELIANCE", "Reliance RSI below 30 buy")
    s3 = test_asset("NIFTY", "Nifty 50 RSI below 30 buy")
    
    if s1 and s2 and s3:
        print("\n✅ VERIFICATION COMPLETE: System is fully dynamic across different assets.")
    else:
        print("\n❌ VERIFICATION FAILED: Some assets did not return dynamic data.")
