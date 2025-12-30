#!/usr/bin/env python3
"""
Explore different time intervals and date ranges on CPAU portal
Captures API request payloads for different granularities
"""

import json
import asyncio
from datetime import datetime, timedelta
from playwright.async_api import async_playwright


async def explore_intervals():
    """Capture API requests for different time intervals"""

    with open('../../secrets.json', 'r') as f:
        creds = json.load(f)

    captured_requests = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Capture LoadUsage requests
        async def capture_request(request):
            if 'LoadUsage' in request.url:
                req_data = {
                    'timestamp': datetime.now().isoformat(),
                    'url': request.url,
                    'method': request.method,
                    'post_data': request.post_data
                }
                captured_requests.append(req_data)
                print(f"\n{'='*80}")
                print(f"Captured LoadUsage request")
                print(f"POST data: {request.post_data}")
                print(f"{'='*80}\n")

        page.on('request', capture_request)

        # Login
        print("Logging in...")
        await page.goto('https://mycpau.cityofpaloalto.org/Portal')
        await page.wait_for_load_state('networkidle')

        await page.fill('#txtLogin', creds['userid'])
        await page.fill('#txtpwd', creds['password'])
        await page.press('#txtpwd', 'Enter')

        await asyncio.sleep(2)
        await page.wait_for_load_state('networkidle')

        # Navigate to Usages page
        print("Navigating to Usages page...")
        await page.goto('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx',
                       wait_until='domcontentloaded',
                       timeout=60000)

        await asyncio.sleep(3)
        print("\n=== Default view (Monthly) captured ===\n")

        # Now let's try to trigger different granularities
        # We'll need to interact with the page controls

        # Wait for user to manually change views
        print("Please manually change the view to DAILY and wait a moment...")
        await asyncio.sleep(15)

        print("Please manually change the view to HOURLY and wait a moment...")
        await asyncio.sleep(15)

        print("Please manually change to a specific date range if possible...")
        await asyncio.sleep(15)

        await browser.close()

    # Save captured requests
    with open('interval_requests.json', 'w') as f:
        json.dump(captured_requests, f, indent=2)

    print(f"\nCaptured {len(captured_requests)} LoadUsage requests")
    print("Saved to interval_requests.json")

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY OF CAPTURED REQUESTS")
    print("="*80)
    for i, req in enumerate(captured_requests, 1):
        print(f"\nRequest #{i}:")
        if req['post_data']:
            try:
                payload = json.loads(req['post_data'])
                print(f"  Mode: {payload.get('Mode', 'N/A')}")
                print(f"  Type: {payload.get('Type', 'N/A')}")
                print(f"  hourlyType: {payload.get('hourlyType', 'N/A')}")
                print(f"  strDate: {payload.get('strDate', 'N/A')}")
                print(f"  DateFromDaily: {payload.get('DateFromDaily', 'N/A')}")
                print(f"  DateToDaily: {payload.get('DateToDaily', 'N/A')}")
            except:
                print(f"  Raw: {req['post_data'][:200]}")


if __name__ == '__main__':
    asyncio.run(explore_intervals())
