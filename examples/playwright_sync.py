"""Open a page with a generated fingerprint (synchronous Playwright).

    pip install 'fpforge[playwright]' && playwright install chromium
    python examples/playwright_sync.py --url https://example.com
    python examples/playwright_sync.py --country DE --proxy http://user:pass@host:8080
    python examples/playwright_sync.py --user-data-dir ./profiles/shop-1   # persistent profile
"""
import argparse

from playwright.sync_api import sync_playwright

from fpforge import FingerprintGenerator
from fpforge.injector.sync_api import launch_context

ap = argparse.ArgumentParser()
ap.add_argument("--url", default="https://example.com")
ap.add_argument("--os", default="windows", choices=["windows", "macos", "linux"])
ap.add_argument("--country", help="must match the proxy's exit country")
ap.add_argument("--proxy")
ap.add_argument("--user-data-dir")
ap.add_argument("--headless", action="store_true")
args = ap.parse_args()

profile = FingerprintGenerator().generate(os=args.os, browser="chrome", country=args.country)
with sync_playwright() as p, launch_context(
    p, profile, headless=args.headless, proxy=args.proxy, user_data_dir=args.user_data_dir
) as session:
    page = session.new_page()
    page.goto(args.url)
    print(page.title())
    print(page.evaluate("() => [navigator.userAgent, navigator.platform, screen.width + 'x' + screen.height]"))
