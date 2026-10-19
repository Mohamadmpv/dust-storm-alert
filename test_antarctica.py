import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("ANTARCTICA_TELEGRAM_TOKEN")

print("=" * 60)
print("ANTARCTICA_TELEGRAM_TOKEN is:", repr(token))
print("Length:", len(token) if token else 0)
print("=" * 60)

if token:
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        r = requests.get(url, timeout=10)
        print("Status Code:", r.status_code)
        print("Response:", r.text)
    except Exception as e:
        print("Error:", e)
else:
    print("Token is None!")