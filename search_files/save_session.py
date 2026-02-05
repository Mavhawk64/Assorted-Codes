import os

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
STATE_PATH = "storage_state.json"
START_URL = os.getenv("URL") or ""  # change

START_URL += "/multimedia-search?keys=epstein&page=1"  # adjust as needed


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(START_URL)

        print("Complete any required verification/login manually.")
        print("When you can use the search page normally, press Enter here...")
        input()

        context.storage_state(path=STATE_PATH)
        browser.close()


if __name__ == "__main__":
    main()
