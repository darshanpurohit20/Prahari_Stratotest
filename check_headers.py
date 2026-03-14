import requests

try:
    url = "http://localhost:8000"
    response = requests.get(url, timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Headers: {response.headers}")
except Exception as e:
    print(f"Error on 8000: {e}")

try:
    url = "http://localhost:8001"
    response = requests.get(url, timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Headers: {response.headers}")
except Exception as e:
    print(f"Error on 8001: {e}")
