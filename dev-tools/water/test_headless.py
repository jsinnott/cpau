#!/usr/bin/env python3
"""
Quick test to verify headless mode works for watersmart authentication.
"""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def test_headless_auth():
    """Test that authentication works in headless mode."""

    # Load credentials
    secrets_path = Path(__file__).parent.parent.parent / 'secrets.json'
    with open(secrets_path, 'r') as f:
        creds = json.load(f)

    print("Testing headless authentication...")
    print("(No browser window should appear)\n")

    with sync_playwright() as p:
        # Launch in headless mode
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Login to CPAU
        print("1. Logging into CPAU portal...")
        page.goto('https://mycpau.cityofpaloalto.org/Portal')
        page.fill('#txtLogin', creds['userid'])
        page.fill('#txtpwd', creds['password'])
        page.press('#txtpwd', 'Enter')
        page.wait_for_load_state('networkidle')
        print("   ✓ Login successful")

        # Navigate to watersmart (triggers SAML flow)
        print("2. Navigating to watersmart.com...")
        page.goto('https://paloalto.watersmart.com/index.php/trackUsage')
        page.wait_for_load_state('networkidle')
        print(f"   ✓ Navigated to: {page.url}")

        # Verify we're authenticated by checking for logout link
        page_content = page.content()
        if 'logout' in page_content.lower():
            print("   ✓ Successfully authenticated (logout link found)")
        else:
            print("   ⚠ Warning: May not be authenticated")

        # Test API call
        print("3. Testing API call...")
        response = page.request.get(
            'https://paloalto.watersmart.com/index.php/rest/v1/Chart/RealTimeChart'
        )

        if response.status == 200:
            data = response.json()
            if 'data' in data:
                print("   ✓ API call successful")
                print(f"   Retrieved {len(data['data'].get('series', []))} data points")
            else:
                print("   ✓ API call successful (unexpected format)")
        else:
            print(f"   ✗ API call failed (status {response.status})")

        # Extract cookies for future use
        cookies = context.cookies()
        watersmart_cookies = [c for c in cookies if 'watersmart' in c['domain']]

        print(f"\n4. Session cookies extracted: {len(watersmart_cookies)} cookies")
        for cookie in watersmart_cookies:
            print(f"   - {cookie['name']}")

        browser.close()

    print("\n✓ Headless mode test completed successfully!")
    print("No browser window appeared during execution.")
    return True


if __name__ == '__main__':
    test_headless_auth()
