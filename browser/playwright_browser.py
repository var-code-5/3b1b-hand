# browser/playwright_browser.py
# Playwright wrapper for safe browser actions

from playwright.sync_api import sync_playwright, Page, Browser
from PIL import Image
import io
import os

class PlaywrightBrowser:
    def __init__(self, headless: bool = False):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.page = self.browser.new_page()
        self.screenshot_dir = "screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def navigate(self, url: str):
        self.page.goto(url)

    def click(self, x: int, y: int):
        self.page.mouse.click(x, y)

    def type_text(self, text: str):
        self.page.keyboard.type(text)

    def scroll(self, delta: int):
        self.page.mouse.wheel(0, delta)

    def wait(self, ms: int):
        self.page.wait_for_timeout(ms)

    def take_screenshot(self, filename: str):
        screenshot = self.page.screenshot()
        img = Image.open(io.BytesIO(screenshot))
        img.save(os.path.join(self.screenshot_dir, filename))

    def close(self):
        self.browser.close()
        self.playwright.stop()
