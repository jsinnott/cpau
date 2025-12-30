#!/usr/bin/env python3
"""
CPAU Meter Data Scraper
Automates login and data retrieval from City of Palo Alto Utilities portal
"""

import json
import asyncio
from playwright.async_api import async_playwright


async def load_credentials():
    """Load credentials from secrets.json"""
    with open('../../secrets.json', 'r') as f:
        return json.load(f)


async def scrape_meter_data():
    """Main function to scrape meter data from CPAU portal"""

    # Load credentials
    creds = await load_credentials()

    # Store captured network requests
    network_requests = []

    async with async_playwright() as p:
        # Launch browser (headless=False to see what's happening)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Set up network request logging
        async def log_request(request):
            network_requests.append({
                'url': request.url,
                'method': request.method,
                'resource_type': request.resource_type
            })
            print(f"[REQUEST] {request.method} {request.url}")

        async def log_response(response):
            print(f"[RESPONSE] {response.status} {response.url}")

        page.on('request', log_request)
        page.on('response', log_response)

        # Navigate to login page
        print("Navigating to login page...")
        await page.goto('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx')

        # Wait for page to load
        await page.wait_for_load_state('networkidle')

        # Take a screenshot to see what we're working with
        await page.screenshot(path='login_page.png')
        print("Screenshot of login page saved to login_page.png")

        # Fill in login credentials
        print("Entering credentials...")
        await page.fill('#txtLogin', creds['userid'])
        await page.fill('#txtpwd', creds['password'])

        # Submit login form and wait for response
        print("Submitting login form...")

        # Set up a response listener for the validateLogin API call
        login_response = None

        async def handle_login_response(response):
            nonlocal login_response
            if 'validateLogin' in response.url:
                login_response = response
                print(f"Login API response: {response.status}")
                try:
                    response_text = await response.text()
                    print(f"Response body: {response_text}")
                except:
                    pass

        page.on('response', handle_login_response)

        try:
            # Press Enter on password field to submit
            await page.press('#txtpwd', 'Enter')
        except Exception as e:
            print(f"Error submitting login: {e}")

        # Wait for the validateLogin response
        print("Waiting for login response...")
        for i in range(30):  # Wait up to 3 seconds
            if login_response:
                break
            await asyncio.sleep(0.1)

        # Wait a bit more for any redirects or page changes
        await asyncio.sleep(2)
        await page.wait_for_load_state('networkidle')

        # Check if we're on the usages page or need to navigate
        current_url = page.url
        print(f"Current URL after login: {current_url}")

        if 'Usages.aspx' not in current_url:
            print("Navigating to Usages page...")
            try:
                await page.goto('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx',
                               wait_until='networkidle',
                               timeout=60000)
            except Exception as e:
                print(f"Error navigating to Usages page: {e}")
                # Try one more time with a different approach
                try:
                    await page.goto('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx',
                                   wait_until='domcontentloaded',
                                   timeout=60000)
                    await asyncio.sleep(2)
                except Exception as e2:
                    print(f"Second attempt failed: {e2}")
                    print("Taking screenshot of current page...")
                    await page.screenshot(path='error_page.png')
                    raise

        # Wait a bit more to capture any additional API calls
        print("Waiting for page to fully load and capture network traffic...")
        await asyncio.sleep(3)

        # Print summary of network requests
        print("\n" + "="*80)
        print("NETWORK REQUESTS SUMMARY")
        print("="*80)

        # Filter for interesting requests (XHR, Fetch, API-like endpoints)
        api_requests = [
            req for req in network_requests
            if req['resource_type'] in ['xhr', 'fetch'] or
               any(term in req['url'].lower() for term in ['api', 'usage', 'meter', 'data', 'export'])
        ]

        if api_requests:
            print("\nPotential API endpoints:")
            for req in api_requests:
                print(f"  {req['method']} {req['url']}")
        else:
            print("\nNo obvious API endpoints found. All requests:")
            for req in network_requests:
                print(f"  {req['method']} {req['url']} ({req['resource_type']})")

        # Take a screenshot for reference
        await page.screenshot(path='usages_page.png')
        print("\nScreenshot saved to usages_page.png")

        # Keep browser open for manual inspection
        print("\nBrowser will remain open for 30 seconds for manual inspection...")
        await asyncio.sleep(30)

        await browser.close()

        return network_requests


if __name__ == '__main__':
    asyncio.run(scrape_meter_data())
