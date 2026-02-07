import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Show browser
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    page = context.new_page()

    print("Loading page...")
    page.goto("https://visa.vfsglobal.com/aze/en/ita/login")

    print("Waiting 10 seconds...")
    page.wait_for_timeout(10000)

    # Take a screenshot
    page.screenshot(path="login_page.png")
    print("Screenshot saved to login_page.png")

    # Print page HTML
    html = page.content()
    with open("page_source.html", "w") as f:
        f.write(html)
    print("HTML saved to page_source.html")

    input("Press Enter to close browser...")
    browser.close()
