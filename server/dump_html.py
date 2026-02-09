import asyncio
from playwright.async_api import async_playwright

async def dump():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Mobile context
        context = await browser.new_context(
            viewport={'width': 390, 'height': 844},
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        page = await context.new_page()
        print("Navigating...")
        await page.goto("https://m.andar.co.kr/product/search.html?keyword=MOFLS-18", wait_until="networkidle")
        content = await page.content()
        with open("server/debug.html", "w") as f:
            f.write(content)
        print("Done dumping to server/debug.html")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(dump())
