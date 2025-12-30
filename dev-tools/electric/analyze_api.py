#!/usr/bin/env python3
"""
CPAU API Analyzer
Captures and analyzes API responses from the usage page
"""

import json
import asyncio
from playwright.async_api import async_playwright


async def load_credentials():
    """Load credentials from secrets.json"""
    with open('../../secrets.json', 'r') as f:
        return json.load(f)


async def analyze_apis():
    """Analyze API calls to understand data structure"""

    creds = await load_credentials()
    api_responses = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Capture API responses
        async def handle_response(response):
            url = response.url

            # Check if this is one of our target API endpoints
            if any(endpoint in url for endpoint in ['LoadUsage', 'BindMultiMeter', 'IsInverted', 'BindColorCodes']):
                try:
                    response_text = await response.text()
                    api_responses[url] = {
                        'status': response.status,
                        'headers': dict(response.headers),
                        'body': response_text
                    }
                    print(f"\n{'='*80}")
                    print(f"Captured API: {url}")
                    print(f"Status: {response.status}")
                    print(f"Response: {response_text[:500]}...")
                    print(f"{'='*80}\n")
                except Exception as e:
                    print(f"Error capturing response from {url}: {e}")

        page.on('response', handle_response)

        # Navigate to login page
        print("Logging in...")
        await page.goto('https://mycpau.cityofpaloalto.org/Portal')
        await page.wait_for_load_state('networkidle')

        # Login
        await page.fill('#txtLogin', creds['userid'])
        await page.fill('#txtpwd', creds['password'])
        await page.press('#txtpwd', 'Enter')

        # Wait for login to complete
        await asyncio.sleep(3)
        await page.wait_for_load_state('networkidle')

        # Navigate to Usages page
        print("Navigating to Usages page...")
        await page.goto('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx',
                       wait_until='domcontentloaded',
                       timeout=60000)

        # Wait for API calls to complete
        print("Waiting for API calls to complete...")
        await asyncio.sleep(5)

        # Save all API responses to a file
        with open('api_responses.json', 'w') as f:
            json.dump(api_responses, f, indent=2)

        print(f"\nCaptured {len(api_responses)} API responses")
        print("Saved to api_responses.json")

        # List the APIs we captured
        print("\nCaptured APIs:")
        for url in api_responses.keys():
            print(f"  - {url}")

        await browser.close()

        return api_responses


if __name__ == '__main__':
    asyncio.run(analyze_apis())
