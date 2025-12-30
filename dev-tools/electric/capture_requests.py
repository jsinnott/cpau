#!/usr/bin/env python3
"""
Capture exact API request payloads
"""

import json
import asyncio
from playwright.async_api import async_playwright


async def capture_api_requests():
    """Capture the exact API requests made by the page"""

    with open('../../secrets.json', 'r') as f:
        creds = json.load(f)

    captured_requests = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Capture requests
        async def capture_request(request):
            if any(api in request.url for api in ['LoadUsage', 'BindMultiMeter']):
                req_data = {
                    'url': request.url,
                    'method': request.method,
                    'headers': dict(request.headers),
                    'post_data': request.post_data
                }
                captured_requests.append(req_data)
                print(f"\n{'='*80}")
                print(f"API: {request.url.split('/')[-1]}")
                print(f"POST data: {request.post_data}")
                print(f"{'='*80}\n")

        page.on('request', capture_request)

        # Login and navigate
        await page.goto('https://mycpau.cityofpaloalto.org/Portal')
        await page.wait_for_load_state('networkidle')

        await page.fill('#txtLogin', creds['userid'])
        await page.fill('#txtpwd', creds['password'])
        await page.press('#txtpwd', 'Enter')

        await asyncio.sleep(2)
        await page.wait_for_load_state('networkidle')

        # Navigate to Usages page
        await page.goto('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx',
                       wait_until='domcontentloaded',
                       timeout=60000)

        await asyncio.sleep(5)

        await browser.close()

    # Save captured requests
    with open('captured_requests.json', 'w') as f:
        json.dump(captured_requests, f, indent=2)

    print(f"\nCaptured {len(captured_requests)} API requests")
    print("Saved to captured_requests.json")


if __name__ == '__main__':
    asyncio.run(capture_api_requests())
