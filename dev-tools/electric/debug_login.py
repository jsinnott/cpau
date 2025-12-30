#!/usr/bin/env python3
"""
Debug login process
"""

import json
import asyncio
from playwright.async_api import async_playwright


async def debug_login():
    """Capture the exact login request"""

    with open('../../secrets.json', 'r') as f:
        creds = json.load(f)

    login_request = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Capture the login request
        async def capture_request(request):
            nonlocal login_request
            if 'validateLogin' in request.url:
                login_request = {
                    'url': request.url,
                    'method': request.method,
                    'headers': dict(request.headers),
                    'post_data': request.post_data
                }
                print("Captured login request:")
                print(f"URL: {request.url}")
                print(f"Method: {request.method}")
                print(f"Headers: {json.dumps(dict(request.headers), indent=2)}")
                print(f"POST data: {request.post_data}")

        page.on('request', capture_request)

        # Navigate and login
        await page.goto('https://mycpau.cityofpaloalto.org/Portal')
        await page.wait_for_load_state('networkidle')

        # Fill and submit
        await page.fill('#txtLogin', creds['userid'])
        await page.fill('#txtpwd', creds['password'])
        await page.press('#txtpwd', 'Enter')

        # Wait for the request
        await asyncio.sleep(3)

        await browser.close()

        return login_request


if __name__ == '__main__':
    result = asyncio.run(debug_login())
    if result:
        print("\nSaved request data:")
        print(json.dumps(result, indent=2))
