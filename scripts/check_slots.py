import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

USER_EMAIL = os.getenv('USER_EMAIL')
USER_PASSWORD = os.getenv('USER_PASSWORD')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_PERSONAL_CHAT_ID = os.getenv('TELEGRAM_PERSONAL_CHAT_ID')
TELEGRAM_GROUP_CHAT_ID = os.getenv('TELEGRAM_GROUP_CHAT_ID')

# API Configuration
BASE_URL = "https://lift-api.vfsglobal.com"
LOGIN_URL = f"{BASE_URL}/user/login"
SLOT_CHECK_URL = f"{BASE_URL}/appointment/CheckIsSlotAvailable"

# Request Configuration
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json;charset=UTF-8",
    "origin": "https://visa.vfsglobal.com",
    "referer": "https://visa.vfsglobal.com/",
    "route": "aze/en/ita",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
}

def send_telegram_message(message):
    """Send a message via Telegram bot to both personal and group chats"""
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️  Telegram bot token not configured")
        return False

    # Collect all chat IDs
    chat_ids = []
    if TELEGRAM_PERSONAL_CHAT_ID:
        chat_ids.append(('personal', TELEGRAM_PERSONAL_CHAT_ID))
    if TELEGRAM_GROUP_CHAT_ID:
        chat_ids.append(('group', TELEGRAM_GROUP_CHAT_ID))

    if not chat_ids:
        print("⚠️  No Telegram chat IDs configured")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    success_count = 0

    for chat_type, chat_id in chat_ids:
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                print(f"✅ Telegram message sent successfully to {chat_type} chat")
                success_count += 1
            else:
                print(f"❌ Failed to send Telegram message to {chat_type} chat: {response.status_code}")
        except Exception as e:
            print(f"❌ Error sending Telegram message to {chat_type} chat: {e}")

    return success_count > 0

def login_with_playwright():
    """Login using Playwright to handle client-side encryption"""
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

        print("🔐 Logging in with Playwright...")

        with sync_playwright() as p:
            # Launch browser with better settings
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled'
                ]
            )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                locale='en-US'
            )

            page = context.new_page()
            page.set_default_timeout(60000)  # 60 second timeout

            # Intercept API responses to capture the access token
            access_token = None

            def handle_response(response):
                nonlocal access_token
                if "user/login" in response.url and response.status == 200:
                    try:
                        data = response.json()
                        if data.get('accessToken'):
                            access_token = data['accessToken']
                            print("✅ Access token captured from API response")
                    except:
                        pass

            page.on("response", handle_response)

            # Navigate to VFS Global visa page
            print("📄 Loading login page...")
            page.goto("https://visa.vfsglobal.com/aze/en/ita/login", wait_until="domcontentloaded", timeout=60000)

            # Wait for potential Cloudflare challenge
            print("⏳ Waiting for page to fully load (Cloudflare check)...")
            page.wait_for_timeout(5000)

            # Handle cookie consent banner
            print("🍪 Checking for cookie consent banner...")
            try:
                # Try to click "Accept All" or "Accept" button
                cookie_buttons = [
                    'button:has-text("Accept All")',
                    'button:has-text("Accept")',
                    'button:has-text("Allow All")',
                    '#onetrust-accept-btn-handler',
                    '.accept-cookies-button',
                    'button.onetrust-close-btn-handler'
                ]
                for selector in cookie_buttons:
                    try:
                        page.click(selector, timeout=3000)
                        print(f"✅ Dismissed cookie banner using: {selector}")
                        page.wait_for_timeout(2000)
                        break
                    except:
                        continue
            except Exception as e:
                print(f"   No cookie banner found or already dismissed")

            # Check current URL
            current_url = page.url
            print(f"📍 Current URL: {current_url}")

            # If not on login page, navigate there
            if "login" not in current_url.lower():
                print("↪️  Navigating to login page...")
                page.goto("https://visa.vfsglobal.com/aze/en/ita/login", wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(3000)

            # Wait for login form to be visible
            print("🔍 Looking for login form...")

            # Take a screenshot for debugging
            try:
                page.screenshot(path="/tmp/login_page_debug.png")
                print("📸 Screenshot saved to /tmp/login_page_debug.png")
            except:
                pass

            try:
                # Try multiple selectors for email field
                email_selector = None
                for selector in ['input[type="email"]', 'input[name="email"]', '#email', 'input[placeholder*="mail" i]', 'input[id*="mat-input"]']:
                    try:
                        page.wait_for_selector(selector, timeout=10000, state="visible")
                        email_selector = selector
                        print(f"✅ Found email field using selector: {selector}")
                        break
                    except:
                        continue

                if not email_selector:
                    # Print all input fields found
                    inputs = page.query_selector_all('input')
                    print(f"❓ Found {len(inputs)} input fields on page")
                    for i, inp in enumerate(inputs[:5]):  # Show first 5
                        inp_type = inp.get_attribute('type')
                        inp_name = inp.get_attribute('name')
                        inp_id = inp.get_attribute('id')
                        print(f"   Input {i}: type={inp_type}, name={inp_name}, id={inp_id}")
                    raise Exception("Could not find email input field")

                # Try multiple selectors for password field
                password_selector = None
                for selector in ['input[type="password"]', 'input[name="password"]', '#password']:
                    try:
                        page.wait_for_selector(selector, timeout=5000, state="visible")
                        password_selector = selector
                        print(f"✅ Found password field using selector: {selector}")
                        break
                    except:
                        continue

                if not password_selector:
                    raise Exception("Could not find password input field")

                # Fill in login credentials
                print("✍️  Filling in credentials...")
                page.fill(email_selector, USER_EMAIL)
                page.wait_for_timeout(500)
                page.fill(password_selector, USER_PASSWORD)
                page.wait_for_timeout(500)

                # Find and click login button
                print("🖱️  Clicking login button...")
                for selector in ['button[type="submit"]', 'button:has-text("Log in")', 'button:has-text("Sign in")', '.btn-primary']:
                    try:
                        page.click(selector, timeout=5000)
                        print(f"✅ Clicked login button using selector: {selector}")
                        break
                    except:
                        continue

                # Wait for login to complete and token to be captured
                print("⏳ Waiting for login response...")
                page.wait_for_timeout(10000)

            except PlaywrightTimeout as e:
                print(f"⏱️  Timeout waiting for element: {e}")
            except Exception as e:
                print(f"⚠️  Error during login: {e}")

            browser.close()

            if access_token:
                print("✅ Login successful - Access token obtained")
                return access_token
            else:
                print("❌ Failed to obtain access token")
                return None

    except ImportError:
        print("⚠️  Playwright not available")
        return None
    except Exception as e:
        print(f"❌ Playwright login error: {e}")
        return None

def check_slots(access_token):
    """Check for available visa appointment slots"""
    print("🔍 Checking for available slots...")

    headers = HEADERS.copy()
    headers["authorize"] = access_token

    payload = {
        "countryCode": "aze",
        "missionCode": "ita",
        "vacCode": "VACB",
        "visaCategoryCode": "SCS",
        "roleName": "Individual",
        "loginUser": USER_EMAIL,
        "payCode": ""
    }

    try:
        response = requests.post(SLOT_CHECK_URL, json=payload, headers=headers, timeout=15)

        if response.status_code == 200:
            data = response.json()

            # Check if slots are available
            if data.get('earliestDate') or data.get('earliestSlotLists'):
                return {
                    'available': True,
                    'earliest_date': data.get('earliestDate'),
                    'slots': data.get('earliestSlotLists', [])
                }
            else:
                error = data.get('error', {})
                if error.get('code') == 4008:
                    print("ℹ️  No slots available")
                    return {'available': False}
                else:
                    print(f"⚠️  Unexpected response: {data}")
                    return {'available': False}
        else:
            print(f"❌ API request failed: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error checking slots: {e}")
        return None

def main():
    """Main execution function"""
    print("=" * 60)
    print("🇮🇹 VFS Global Italy Visa Slot Checker")
    print(f"⏰ Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Validate all required environment variables
    required_vars = {
        'USER_EMAIL': USER_EMAIL,
        'USER_PASSWORD': USER_PASSWORD,
        'TELEGRAM_BOT_TOKEN': TELEGRAM_BOT_TOKEN,
        'TELEGRAM_PERSONAL_CHAT_ID': TELEGRAM_PERSONAL_CHAT_ID
    }

    missing_vars = [var_name for var_name, var_value in required_vars.items() if not var_value]

    if missing_vars:
        print(f"❌ Error: The following environment variables must be set: {', '.join(missing_vars)}")
        sys.exit(1)

    # Step 1: Login to get access token
    access_token = login_with_playwright()

    if not access_token:
        print("❌ Failed to login - cannot check slots")
        sys.exit(1)

    # Step 2: Check for available slots
    result = check_slots(access_token)

    if result is None:
        print("❌ Failed to check slots")
        sys.exit(1)

    # Step 3: Send notification if slots are available
    if result['available']:
        earliest_date = result.get('earliest_date', 'Unknown')
        slots_count = len(result.get('slots', []))

        message = f"""
🎉 <b>VISA SLOT AVAILABLE!</b> 🎉

📅 <b>Earliest Date:</b> {earliest_date}
🔢 <b>Available Slots:</b> {slots_count}
⏰ <b>Detected At:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔗 <b>Book Now:</b> https://visa.vfsglobal.com/aze/en/ita/

⚡ Act fast! Slots may fill up quickly.
        """.strip()

        print("\n🎉 SLOTS AVAILABLE!")
        print(f"📅 Earliest Date: {earliest_date}")
        print(f"🔢 Slots Count: {slots_count}")

        send_telegram_message(message)
    else:
        print("\n❌ No slots currently available")
        # Don't send Telegram message when no slots

    print("\n" + "=" * 60)
    print("✅ Check completed successfully")
    print("=" * 60)

if __name__ == "__main__":
    main()
