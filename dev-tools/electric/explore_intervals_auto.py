#!/usr/bin/env python3
"""
Automatically explore different time intervals on CPAU portal
Tries to programmatically change views and capture API requests
"""

import json
import asyncio
from datetime import datetime, timedelta
from playwright.async_api import async_playwright


async def explore_intervals_auto():
    """Capture API requests for different time intervals by automating UI interactions"""

    with open('../../secrets.json', 'r') as f:
        creds = json.load(f)

    captured_requests = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Capture LoadUsage requests
        async def capture_request(request):
            if 'LoadUsage' in request.url and request.post_data:
                try:
                    payload = json.loads(request.post_data)
                    mode = payload.get('Mode', 'Unknown')

                    if mode not in captured_requests:
                        captured_requests[mode] = []

                    captured_requests[mode].append({
                        'timestamp': datetime.now().isoformat(),
                        'payload': payload
                    })

                    print(f"\nCaptured LoadUsage request - Mode: {mode}")
                    print(f"  Payload: {json.dumps(payload, indent=2)}")
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

        await asyncio.sleep(5)
        print("Default view (Monthly) should be captured")

        # Take a screenshot to see the page structure
        await page.screenshot(path='usages_page_ui.png')
        print("Screenshot saved to usages_page_ui.png")

        # Try to find and list all buttons, selects, and interactive elements
        print("\n" + "="*80)
        print("Looking for UI controls...")
        print("="*80)

        # Find select/dropdown elements
        selects = await page.query_selector_all('select')
        print(f"\nFound {len(selects)} select elements:")
        for i, select in enumerate(selects):
            select_id = await select.get_attribute('id')
            select_name = await select.get_attribute('name')
            print(f"  Select #{i}: id='{select_id}', name='{select_name}'")

            # Get options
            options = await select.query_selector_all('option')
            print(f"    Options ({len(options)}):")
            for opt in options[:10]:  # Limit to first 10
                value = await opt.get_attribute('value')
                text = await opt.text_content()
                print(f"      - value='{value}', text='{text}'")

        # Find radio buttons
        radios = await page.query_selector_all('input[type="radio"]')
        print(f"\nFound {len(radios)} radio buttons:")
        for i, radio in enumerate(radios[:20]):  # Limit output
            radio_id = await radio.get_attribute('id')
            radio_name = await radio.get_attribute('name')
            radio_value = await radio.get_attribute('value')
            is_checked = await radio.is_checked()
            print(f"  Radio #{i}: id='{radio_id}', name='{radio_name}', value='{radio_value}', checked={is_checked}")

        # Find buttons
        buttons = await page.query_selector_all('button, input[type="button"], input[type="submit"]')
        print(f"\nFound {len(buttons)} buttons:")
        for i, button in enumerate(buttons[:20]):
            button_id = await button.get_attribute('id')
            button_text = await button.text_content()
            button_value = await button.get_attribute('value')
            print(f"  Button #{i}: id='{button_id}', text='{button_text}', value='{button_value}'")

        # Keep browser open for inspection
        print("\n" + "="*80)
        print("Browser will remain open for 30 seconds for inspection...")
        print("="*80)
        await asyncio.sleep(30)

        await browser.close()

    # Save captured requests
    with open('interval_requests_auto.json', 'w') as f:
        json.dump(captured_requests, f, indent=2)

    print(f"\nCaptured requests for {len(captured_requests)} different modes")
    print("Saved to interval_requests_auto.json")


if __name__ == '__main__':
    asyncio.run(explore_intervals_auto())
