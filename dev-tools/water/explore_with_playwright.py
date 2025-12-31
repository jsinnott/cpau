#!/usr/bin/env python3
"""
Browser automation script to explore watersmart.com authentication and capture API calls.

Uses Playwright to:
1. Navigate through SAML/SSO authentication
2. Capture network requests (especially XHR/Fetch API calls)
3. Save actual page HTML after authentication
4. Extract API endpoints and data structures

Usage:
    ../../bin/python3 explore_with_playwright.py

Requirements:
    playwright must be installed (it's in requirements.txt)
    playwright install must have been run to download browsers
"""

import json
import re
from datetime import datetime
from pathlib import Path


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Error: 'playwright' module not found.")
        print("Install it with: ../../bin/pip install playwright")
        print("Then run: ../../bin/playwright install")
        return 1

    # Load credentials
    secrets_path = Path(__file__).parent.parent.parent / 'secrets.json'
    with open(secrets_path, 'r') as f:
        creds = json.load(f)

    print("\n" + "=" * 70)
    print("CPAU Watersmart.com Browser Automation Explorer")
    print("=" * 70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Track network requests
    api_requests = []

    def handle_request(request):
        """Capture API requests (XHR and Fetch)"""
        if request.resource_type in ['xhr', 'fetch']:
            api_requests.append({
                'url': request.url,
                'method': request.method,
                'headers': dict(request.headers),
                'post_data': request.post_data,
            })
            print(f"  API Call: {request.method} {request.url}")

    def handle_response(response):
        """Capture API responses"""
        if response.request.resource_type in ['xhr', 'fetch']:
            try:
                # Try to get response body
                body = response.body()
                content_type = response.headers.get('content-type', '')

                # Store response data
                for req in api_requests:
                    if req['url'] == response.url:
                        req['status'] = response.status
                        req['response_headers'] = dict(response.headers)

                        # Try to decode response
                        if 'json' in content_type:
                            try:
                                req['response_body'] = json.loads(body)
                            except:
                                req['response_body'] = body.decode('utf-8', errors='ignore')
                        else:
                            req['response_body'] = body.decode('utf-8', errors='ignore')[:1000]
                        break
            except Exception as e:
                print(f"  Warning: Could not capture response body: {e}")

    with sync_playwright() as p:
        # Launch browser (headless=False to see what's happening, set to True for automation)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Set up request/response handlers
        page.on('request', handle_request)
        page.on('response', handle_response)

        # Step 1: Login to CPAU
        print("STEP 1: Logging into CPAU Portal")
        print("-" * 70)

        print("Navigating to CPAU homepage...")
        page.goto('https://mycpau.cityofpaloalto.org/Portal')
        page.wait_for_load_state('networkidle')
        print("✓ Homepage loaded")

        # Save the homepage HTML to debug selectors
        homepage_html = page.content()
        Path('/tmp/cpau_homepage.html').write_text(homepage_html)
        print("  Saved homepage HTML for debugging")

        # Fill in login credentials (same as electric meter scripts)
        print("Entering credentials...")
        page.fill('#txtLogin', creds['userid'])
        page.fill('#txtpwd', creds['password'])

        # Submit login form by pressing Enter
        print("Submitting login...")
        page.press('#txtpwd', 'Enter')

        # Wait for login to complete
        page.wait_for_load_state('networkidle')
        print("✓ Login complete\n")

        # Step 2: Navigate to watersmart.com
        print("STEP 2: Navigating to Watersmart.com")
        print("-" * 70)

        # Try to find the watersmart link on the CPAU portal
        # If that doesn't work, navigate directly
        print("Looking for WaterSmart link...")
        try:
            # Look for link containing "water" (case insensitive)
            water_link = page.locator('a:has-text("Water")').first
            if water_link.is_visible():
                print("Found WaterSmart link, clicking...")
                water_link.click()
            else:
                print("No link found, navigating directly to paloalto.watersmart.com...")
                page.goto('https://paloalto.watersmart.com')
        except:
            print("Error finding link, navigating directly...")
            page.goto('https://paloalto.watersmart.com')

        page.wait_for_load_state('networkidle')
        print(f"✓ Navigated to: {page.url}\n")

        # Step 3: Navigate to Track Usage page
        print("STEP 3: Accessing Track Usage Page")
        print("-" * 70)

        print("Navigating to Track Usage...")
        page.goto('https://paloalto.watersmart.com/index.php/trackUsage')
        page.wait_for_load_state('networkidle')

        # Wait for charts to load (they make API calls)
        print("Waiting for charts to load...")
        page.wait_for_timeout(3000)  # Wait 3 seconds for any delayed API calls

        print(f"✓ Track Usage page loaded")
        print(f"  Current URL: {page.url}")

        # Save the page HTML
        track_usage_html = page.content()
        output_path = Path('/tmp/watersmart_trackUsage_real.html')
        output_path.write_text(track_usage_html)
        print(f"  Saved HTML to: {output_path}\n")

        # Step 4: Navigate to Download page
        print("STEP 4: Accessing Download Page")
        print("-" * 70)

        print("Navigating to Download page...")
        page.goto('https://paloalto.watersmart.com/index.php/accountPreferences/download')
        page.wait_for_load_state('networkidle')

        print(f"✓ Download page loaded")
        print(f"  Current URL: {page.url}")

        # Save the page HTML
        download_html = page.content()
        output_path = Path('/tmp/watersmart_download_real.html')
        output_path.write_text(download_html)
        print(f"  Saved HTML to: {output_path}\n")

        # Step 5: Save captured API calls
        print("STEP 5: Saving Captured API Calls")
        print("-" * 70)

        api_log_path = Path('/tmp/watersmart_api_calls.json')
        with open(api_log_path, 'w') as f:
            json.dump(api_requests, f, indent=2)

        print(f"Captured {len(api_requests)} API calls")
        print(f"Saved to: {api_log_path}")

        # Print summary of API calls
        print("\nAPI Call Summary:")
        for i, req in enumerate(api_requests, 1):
            print(f"{i}. {req['method']} {req['url']}")
            if req.get('status'):
                print(f"   Status: {req['status']}")

        print("\n" + "=" * 70)
        print("Browser will close in 10 seconds...")
        print("Check the saved files for API details and page HTML")
        print("=" * 70)

        page.wait_for_timeout(10000)
        browser.close()

    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
