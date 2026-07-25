"""Debug: dump the page content that headless Playwright sees."""
import asyncio
import sys

sys.path.insert(0, ".")
from playwright.async_api import async_playwright

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

async def main():
    url = "https://wellfound.com/role/r/software-engineer"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1440, "height": 900},
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            },
        )
        page = await context.new_page()
        print(f"Navigating to {url} ...")
        resp = await page.goto(url, wait_until="networkidle", timeout=45000)
        print(f"Status: {resp.status}")
        print(f"Final URL: {page.url}")

        # Wait extra time for SPA
        await asyncio.sleep(5)

        title = await page.title()
        print(f"Page title: {title}")

        # Check for Cloudflare / challenge
        body_text = await page.inner_text("body")
        first_500 = body_text[:500].replace("\n", " | ")
        print(f"\nFirst 500 chars of body text:\n{first_500}\n")

        # Count job links
        job_links = await page.query_selector_all('a[href*="/jobs/"]')
        print(f"Job link anchors found: {len(job_links)}")

        # Try broader selectors
        all_anchors = await page.query_selector_all("a")
        print(f"Total anchors on page: {len(all_anchors)}")

        # Check for challenge/login
        challenge = await page.query_selector_all('[class*="challenge"], [class*="captcha"], [id*="challenge"]')
        print(f"Challenge elements: {len(challenge)}")

        # Dump first few anchor hrefs
        for a in all_anchors[:15]:
            href = await a.get_attribute("href")
            txt = (await a.inner_text())[:60]
            print(f"  <a href='{href}'> {txt}")

        # Take a screenshot for visual inspection
        await page.screenshot(path="debug_headless_screenshot.png", full_page=False)
        print("\nScreenshot saved to debug_headless_screenshot.png")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
