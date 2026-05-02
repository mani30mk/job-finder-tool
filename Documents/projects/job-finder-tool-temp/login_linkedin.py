"""LinkedIn login - robust version with retry logic."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import asyncio
from playwright.async_api import async_playwright


async def main():
    email = input("LinkedIn Email: ").strip()
    password = input("LinkedIn Password: ").strip()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=100  # Slow down actions to look more human
        )
        
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        print("[LinkedIn] Opening login page...")
        
        try:
            # Go to login page with longer timeout
            await page.goto("https://www.linkedin.com/login", wait_until="networkidle", timeout=60000)
            
            # Wait for username field with retry
            print("[LinkedIn] Waiting for login form...")
            await page.wait_for_selector("#username", state="visible", timeout=30000)
            
            # Fill credentials with delays
            await page.fill("#username", email)
            await asyncio.sleep(1)
            await page.fill("#password", password)
            await asyncio.sleep(1)
            
            # Click submit
            await page.click("button[type='submit']")
            
            # Wait for navigation
            print("[LinkedIn] Logging in... (complete CAPTCHA/2FA if shown)")
            
            # Wait for either feed or challenge
            await page.wait_for_url(
                lambda url: "feed" in url or "checkpoint" in url or "challenge" in url,
                timeout=120000
            )
            
            if "checkpoint" in page.url or "challenge" in page.url:
                print("[LinkedIn] CAPTCHA/2FA detected! Complete it in the browser.")
                print("[LinkedIn] Waiting for you to finish...")
                await page.wait_for_url(lambda url: "feed" in url, timeout=300000)
            
            # Save session
            session_dir = Path("session_data")
            session_dir.mkdir(exist_ok=True)
            
            await context.storage_state(path=str(session_dir / "linkedin_storage.json"))
            print(f"[LinkedIn] Session saved successfully!")
            
        except Exception as e:
            print(f"[LinkedIn] Error: {e}")
            print("[LinkedIn] Taking screenshot for debugging...")
            await page.screenshot(path="linkedin_error.png")
            print("[LinkedIn] Screenshot saved to linkedin_error.png")
        
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())