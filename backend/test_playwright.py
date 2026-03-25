import asyncio
import sys
from playwright.async_api import async_playwright

async def test():
    print(f"Python version: {sys.version}")
    if sys.platform == "win32":
        print("Setting ProactorEventLoopPolicy...")
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    print(f"Current loop: {type(asyncio.get_event_loop_policy())}")
    
    async with async_playwright() as p:
        print("Playwright started!")
        browser = await p.chromium.launch(headless=True)
        print("Browser launched!")
        await browser.close()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(test())
