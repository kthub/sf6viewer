import os
from playwright.sync_api import sync_playwright

# Credentials
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

def login_and_get_cookies():
    with sync_playwright() as p:
        # Launch the browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # access to the login page
        page.goto("https://www.streetfighter.com/6/buckler/auth/loginep?redirect_url=/")

        # input email and password
        page.fill('input[name="email"]', EMAIL)
        page.fill('input[name="password"]', PASSWORD)

        # click login button
        page.click('button[type="submit"]')

        # wait for the page to load
        page.wait_for_load_state('networkidle')

        # Get buckler_id from cookies
        cookies = page.context.cookies()
        for cookie in cookies:
            if cookie['name'] == 'buckler_id':
                print(f"{cookie['value']}")

        # close the browser
        browser.close()

# Run the function
if __name__ == "__main__":
    login_and_get_cookies()
