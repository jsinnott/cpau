#!/usr/bin/env python3
"""
Capture API requests for all time intervals by clicking the interval buttons
"""

import json
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright


async def capture_all_intervals():
    """Click on each interval button and capture the API requests"""

    with open('../../secrets.json', 'r') as f:
        creds = json.load(f)

    captured_requests = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Capture LoadUsage requests
        async def capture_request(request):
            if 'LoadUsage' in request.url and request.post_data:
                try:
                    payload = json.loads(request.post_data)
                    captured_requests.append({
                        'timestamp': datetime.now().isoformat(),
                        'mode': payload.get('Mode', 'Unknown'),
                        'hourly_type': payload.get('hourlyType', 'Unknown'),
                        'payload': payload
                    })
                    mode = payload.get('Mode', 'Unknown')
                    hourly_type = payload.get('hourlyType', 'Unknown')
                    print(f"Captured: Mode={mode}, hourlyType={hourly_type}")
                except Exception as e:
                    print(f"Error parsing request: {e}")

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
        print("\nNavigating to Usages page...")
        await page.goto('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx',
                       wait_until='domcontentloaded',
                       timeout=60000)

        await asyncio.sleep(3)
        print("\n1. Default view (Monthly) captured")

        # Now try to find and click the interval buttons
        # Looking for elements with title or alt attributes that might indicate intervals

        # Try to find elements by looking for images or links with titles
        print("\nSearching for interval buttons...")

        # Look for all clickable elements with title attributes
        elements = await page.query_selector_all('[title]')
        interval_buttons = {}

        for elem in elements:
            title = await elem.get_attribute('title')
            if title and any(keyword in title.lower() for keyword in ['15 min', 'hourly', 'daily', 'monthly', 'quarter']):
                interval_buttons[title] = elem
                print(f"  Found button: {title}")

        # If we found buttons, click them
        if interval_buttons:
            for title, button in interval_buttons.items():
                print(f"\nClicking on: {title}")
                try:
                    await button.click()
                    await asyncio.sleep(3)  # Wait for the API call
                except Exception as e:
                    print(f"  Error clicking: {e}")
        else:
            print("No interval buttons found by title attribute")
            print("Trying to find by image alt text or other attributes...")

            # Try finding img elements
            imgs = await page.query_selector_all('img')
            for img in imgs:
                alt = await img.get_attribute('alt')
                title = await img.get_attribute('title')
                if (alt and any(kw in alt.lower() for kw in ['15', 'hour', 'day', 'month'])) or \
                   (title and any(kw in title.lower() for kw in ['15', 'hour', 'day', 'month'])):
                    print(f"  Found image: alt='{alt}', title='{title}'")
                    try:
                        # Try clicking the parent element
                        parent = await img.evaluate_handle('el => el.parentElement')
                        await parent.click()
                        await asyncio.sleep(3)
                    except Exception as e:
                        print(f"    Error clicking: {e}")

        # Keep browser open for inspection
        print("\nBrowser will remain open for 20 seconds...")
        await asyncio.sleep(20)

        await browser.close()

    # Save captured requests
    with open('all_interval_requests.json', 'w') as f:
        json.dump(captured_requests, f, indent=2)

    print(f"\n{'='*80}")
    print(f"Captured {len(captured_requests)} total requests")
    print("Saved to all_interval_requests.json")
    print(f"{'='*80}")

    # Print summary
    print("\nSUMMARY:")
    for i, req in enumerate(captured_requests, 1):
        print(f"\n{i}. Mode={req['mode']}, hourlyType={req['hourly_type']}")
        print(f"   Key fields:")
        for key in ['Mode', 'hourlyType', 'Type', 'DateFromDaily', 'DateToDaily', 'strDate']:
            print(f"     {key}: {req['payload'].get(key, 'N/A')}")


if __name__ == '__main__':
    asyncio.run(capture_all_intervals())
