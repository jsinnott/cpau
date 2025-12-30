#!/usr/bin/env python3
"""
Capture the EXACT request that works when we set a date in the UI
"""

import json
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

async def capture_working_request():
    with open('../../secrets.json', 'r') as f:
        creds = json.load(f)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Capture all requests to LoadUsage
        captured_requests = []

        async def handle_request(request):
            if 'LoadUsage' in request.url:
                try:
                    post_data = request.post_data
                    if post_data:
                        payload = json.loads(post_data)
                        captured_requests.append({
                            'timestamp': datetime.now().isoformat(),
                            'url': request.url,
                            'payload': payload,
                            'headers': dict(request.headers)
                        })
                        print(f"\n{'='*80}")
                        print(f"Captured LoadUsage request:")
                        print(f"Payload: {json.dumps(payload, indent=2)}")
                except Exception as e:
                    print(f"Error capturing request: {e}")

        page.on('request', handle_request)

        # Login
        print("Logging in...")
        await page.goto('https://mycpau.cityofpaloalto.org/Portal')
        await page.wait_for_timeout(1000)

        # Fill login form
        await page.fill('input[name="userid"]', creds['userid'])
        await page.fill('input[name="password"]', creds['password'])
        await page.click('input[type="submit"]')
        await page.wait_for_load_state('networkidle')

        # Navigate to Usages
        print("Navigating to Usages page...")
        await page.goto('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx')
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2000)

        # Click 15-minute button
        print("\nClicking 15-minute button...")
        min15_img = page.locator('img[title="15 Minute"]')
        await min15_img.click()
        await page.wait_for_timeout(3000)

        # Now change the date to December 17
        print("\nChanging date to 12/17/25...")

        # Find and fill the date input field
        # The date picker might be in different elements, let's try common patterns
        date_input = page.locator('input[type="text"]').filter(has=page.locator('[placeholder*="Date"]'))
        if await date_input.count() == 0:
            # Try by ID or other attributes
            date_input = page.locator('#txtFromDate, #DateFromDaily, input[id*="Date"]').first

        if await date_input.count() > 0:
            await date_input.click()
            await page.wait_for_timeout(500)
            await date_input.fill('12/17/25')
            await page.wait_for_timeout(500)

            # Trigger the date change - might need to click elsewhere or press Enter
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(3000)
        else:
            print("Could not find date input field")
            # Take a screenshot to see what's on the page
            await page.screenshot(path='date_picker_debug.png')
            print("Screenshot saved to date_picker_debug.png")

        # Wait a bit more to ensure all requests are captured
        await page.wait_for_timeout(2000)

        # Save all captured requests
        if captured_requests:
            with open('working_request.json', 'w') as f:
                json.dump(captured_requests, f, indent=2)
            print(f"\n{'='*80}")
            print(f"Saved {len(captured_requests)} requests to working_request.json")
        else:
            print("\nNo requests captured - date change may not have worked")

        # Keep browser open for inspection
        print("\nBrowser will stay open for 10 seconds for inspection...")
        await page.wait_for_timeout(10000)

        await browser.close()

if __name__ == '__main__':
    asyncio.run(capture_working_request())
