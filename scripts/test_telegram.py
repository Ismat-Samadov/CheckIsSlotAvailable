import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_PERSONAL_CHAT_ID = os.getenv('TELEGRAM_PERSONAL_CHAT_ID')

print(f"Bot Token: {TELEGRAM_BOT_TOKEN[:20]}..." if TELEGRAM_BOT_TOKEN else "Not set")
print(f"Chat ID: {TELEGRAM_PERSONAL_CHAT_ID}")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_PERSONAL_CHAT_ID:
    print("❌ Missing Telegram credentials")
    exit(1)

url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
payload = {
    "chat_id": TELEGRAM_PERSONAL_CHAT_ID,
    "text": "🧪 <b>Test Message</b>\n\nThis is a test from your visa slot checker!",
    "parse_mode": "HTML"
}

print("\nSending test message...")
response = requests.post(url, json=payload, timeout=10)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")

if response.status_code == 200:
    print("\n✅ SUCCESS! Check your Telegram for the test message.")
else:
    print(f"\n❌ FAILED: {response.json()}")
