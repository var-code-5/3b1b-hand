# browser/playwright_browser.py
# Playwright wrapper for safe browser actions

from playwright.sync_api import sync_playwright, Page, Browser
from PIL import Image
import io
import os
from typing import Optional

class PlaywrightBrowser:
    def __init__(self, headless: bool = False):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.firefox.launch(headless=headless)
        self.page = self.browser.new_page(viewport=None)
        self.screenshot_dir = "screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def navigate(self, url: str):
        self.page.goto(url, wait_until="networkidle")

    def scroll(self, delta: int):
        self.page.mouse.wheel(0, delta)

    def wait(self, ms: int):
        self.page.wait_for_timeout(ms)

    def take_screenshot(self, filename: str):
        screenshot = self.page.screenshot()
        img = Image.open(io.BytesIO(screenshot))
        img.save(os.path.join(self.screenshot_dir, filename))
        
    def click_by_text(self, text: str):
        '''Click an element by its visible text.'''
        print(f"Clicking element with text '{text}'")
        self.page.get_by_text(text).first.click()

    def fill_by_label(self, label: str, text: str):
        '''Type text into an input field by its label.'''
        print(f"Filling input with label '{label}' with text '{text}'")
        self.page.get_by_label(label).fill(text)
        
    def close(self):
        self.browser.close()
        self.playwright.stop()