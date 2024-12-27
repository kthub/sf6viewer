import os
from playwright.sync_api import sync_playwright

# Credentials
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

def login_and_get_cookies():
    with sync_playwright() as p:
        # Chromiumブラウザを起動（headless=Falseでブラウザを表示可能）
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # ログインページにアクセス
        page.goto("https://www.streetfighter.com/6/buckler/auth/loginep?redirect_url=/")

        # メールアドレスとパスワードを入力
        page.fill('input[name="email"]', EMAIL)
        page.fill('input[name="password"]', PASSWORD)

        # ログインボタンをクリック
        page.click('button[type="submit"]')

        # ログイン後の処理を待機
        page.wait_for_load_state('networkidle')  # ネットワークリクエストが完了するまで待機

        # Cookieを取得
        cookies = page.context.cookies()

        # Cookieを表示
        for cookie in cookies:
            # buckler_idを出力
            if cookie['name'] == 'buckler_id':
                print(f"{cookie['value']}")

        # ブラウザを閉じる
        browser.close()

# 実行
if __name__ == "__main__":
    login_and_get_cookies()
