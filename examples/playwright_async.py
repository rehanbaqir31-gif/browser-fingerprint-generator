"""Same as playwright_sync.py, with asyncio."""
import asyncio

from playwright.async_api import async_playwright

from fpforge import FingerprintGenerator
from fpforge.injector.async_api import launch_context


async def main() -> None:
    profile = FingerprintGenerator().generate(os="macos", country="US")
    async with async_playwright() as p:
        async with await launch_context(p, profile, headless=True) as session:
            page = await session.new_page()
            await page.goto("https://example.com")
            print(await page.evaluate("() => [navigator.userAgent, navigator.platform]"))


asyncio.run(main())
