#!/usr/bin/env python3
"""
Check what data the UI actually shows for hourly and 15-minute modes
"""

import json
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

async def check_ui_data():
    with open('../../secrets.json', 'r') as f:
        creds = json.load(f)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # Login
        print("Logging in...")
        await page.goto('https://mycpau.cityofpaloalto.org/Portal')
        await page.fill('input[name="userid"]', creds['userid'])
        await page.fill('input[name="password"]', creds['password'])
        await page.click('input[type="submit"]')
        await page.wait_for_load_state('networkidle')

        # Navigate to Usages
        print("Navigating to Usages page...")
        await page.goto('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx')
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)

        # Setup request interception to capture API response
        responses = []

        async def handle_response(response):
            if 'LoadUsage' in response.url:
                try:
                    data = await response.json()
                    responses.append({
                        'url': response.url,
                        'status': response.status,
                        'data': data
                    })
                    print(f"Captured response: {response.status}")
                except Exception as e:
                    print(f"Error capturing response: {e}")

        page.on('response', handle_response)

        # Click hourly button
        print("\nClicking Hourly button...")
        hourly_img = page.locator('img[title="Hourly"]')
        await hourly_img.click()
        await asyncio.sleep(3)

        # Check if there's a chart or data displayed
        print("Checking for chart data...")
        chart_exists = await page.locator('#divUsageChart').is_visible()
        print(f"Chart visible: {chart_exists}")

        # Check for "no data" messages
        no_data = await page.locator('text=/no data/i').count()
        print(f"'No data' messages: {no_data}")

        # Save the responses
        print(f"\nCaptured {len(responses)} API responses")
        if responses:
            # Parse the JSON response
            for i, resp in enumerate(responses):
                print(f"\nResponse {i+1}:")
                print(f"  Status: {resp['status']}")
                if 'd' in resp['data']:
                    parsed = json.loads(resp['data']['d'])
                    records = parsed.get('objUsageGenerationResultSetTwo', [])
                    print(f"  Records: {len(records)}")
                    if records:
                        print(f"  First record: {json.dumps(records[0], indent=4)}")
                    else:
                        print("  No records in objUsageGenerationResultSetTwo")
                        print(f"  Response keys: {list(parsed.keys())}")

        # Try 15-minute mode
        print("\n" + "="*80)
        print("Clicking 15-minute button...")
        responses.clear()
        min15_img = page.locator('img[title="15 Minute"]')
        await min15_img.click()
        await asyncio.sleep(3)

        print(f"\nCaptured {len(responses)} API responses for 15-minute")
        if responses:
            for i, resp in enumerate(responses):
                print(f"\nResponse {i+1}:")
                print(f"  Status: {resp['status']}")
                if 'd' in resp['data']:
                    parsed = json.loads(resp['data']['d'])
                    records = parsed.get('objUsageGenerationResultSetTwo', [])
                    print(f"  Records: {len(records)}")

        # Keep browser open for inspection
        print("\nBrowser will stay open for 10 seconds for inspection...")
        await asyncio.sleep(10)

        await browser.close()

if __name__ == '__main__':
    asyncio.run(check_ui_data())
