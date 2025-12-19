# main.py
# CLI entry point

import argparse
from planner import Planner
from controller import Controller
from browser.playwright_browser import PlaywrightBrowser
from vlm.qwen_client import QwenClient
import os

def main():
    parser = argparse.ArgumentParser(description="Vision-based Browser Automation Agent")
    parser.add_argument("intent", help="User intent, e.g., 'Send 500 Rs to Rohit'")
    parser.add_argument("--openai_key", default=os.getenv("OPENAI_API_KEY"))
    parser.add_argument("--qwen_key", default=os.getenv("QWEN_API_KEY"))  # Assuming env var
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--qwen_url", default=os.getenv("QWEN_URL"))

    args = parser.parse_args()

    planner = Planner(args.openai_key)
    browser = PlaywrightBrowser(headless=args.headless)
    vlm = QwenClient(args.qwen_key,base_url=args.qwen_url)

    controller = Controller(planner, browser, vlm)
    try:
        controller.run(args.intent)
    finally:
        browser.close()

if __name__ == "__main__":
    main()
