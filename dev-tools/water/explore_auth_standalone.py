#!/usr/bin/env python3
"""
Standalone authentication explorer for watersmart.com.

This script can be run with any Python 3 that has 'requests' installed.
It does not depend on the cpau library.

Usage:
    python3 explore_auth_standalone.py

Requirements:
    pip install requests
"""

import json
import re
from datetime import datetime


def main():
    try:
        import requests
    except ImportError:
        print("Error: 'requests' module not found.")
        print("Install it with: pip install requests")
        return 1

    # Load credentials
    with open('../../secrets.json', 'r') as f:
        creds = json.load(f)

    print("\n" + "=" * 70)
    print("CPAU to Watersmart.com Authentication Explorer (Standalone)")
    print("=" * 70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Create session
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })

    # Step 1: Login to CPAU
    print("STEP 1: Logging into CPAU Portal")
    print("-" * 70)

    # Get homepage
    print("Getting CPAU homepage...")
    homepage = session.get('https://mycpau.cityofpaloalto.org/Portal')
    if homepage.status_code != 200:
        print(f"✗ Failed to load homepage (status {homepage.status_code})")
        return 1
    print(f"✓ Homepage loaded")

    # Extract CSRF token
    csrf_match = re.search(r'name="__RequestVerificationToken".*?value="([^"]+)"', homepage.text)
    csrf_token = csrf_match.group(1) if csrf_match else None
    if csrf_token:
        print(f"✓ CSRF token: {csrf_token[:30]}...")

    # Login
    print("Submitting login...")
    login_response = session.post(
        'https://mycpau.cityofpaloalto.org/Portal/Default.aspx/validateLogin',
        json={
            'username': creds['userid'],
            'password': creds['password'],
            'rememberme': False,
            'calledFrom': 'LN',
            'ExternalLoginId': '',
            'LoginMode': '1'
        },
        headers={
            'Content-Type': 'application/json; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'csrftoken': csrf_token if csrf_token else '',
        }
    )

    if login_response.status_code == 200:
        print("✓ Login successful\n")
    else:
        print(f"✗ Login failed (status {login_response.status_code})\n")
        return 1

    # Step 2: Try to access watersmart.com
    print("STEP 2: Attempting to Access Watersmart.com")
    print("-" * 70)

    test_urls = [
        'https://paloalto.watersmart.com',
        'https://paloalto.watersmart.com/index.php/welcome',
        'https://paloalto.watersmart.com/index.php/trackUsage',
        'https://paloalto.watersmart.com/index.php/accountPreferences/download',
    ]

    for url in test_urls:
        print(f"\nTrying: {url}")
        try:
            response = session.get(url, allow_redirects=True)
            print(f"  Final URL: {response.url}")
            print(f"  Status: {response.status_code}")

            # Check if we got redirected to a login page
            if 'login' in response.url.lower() or 'signin' in response.url.lower():
                print(f"  ⚠ Redirected to login - NOT authenticated")
            elif response.status_code == 200:
                print(f"  ✓ Access successful")

                # Check for logout link as authentication indicator
                if 'logout' in response.text.lower():
                    print(f"  ✓ Found logout link - appears authenticated")

                # Save page
                filename = url.split('/')[-1] or 'index'
                filepath = f"/tmp/watersmart_{filename}.html"
                with open(filepath, 'w') as f:
                    f.write(response.text)
                print(f"  Saved to: {filepath}")

        except Exception as e:
            print(f"  ✗ Error: {e}")

    # Step 3: Display cookies
    print("\n" + "=" * 70)
    print("STEP 3: Session Cookies")
    print("-" * 70)

    cpau_cookies = []
    watersmart_cookies = []

    for cookie in session.cookies:
        cookie_info = f"{cookie.name} = {cookie.value[:30]}..."
        if 'watersmart' in cookie.domain:
            watersmart_cookies.append(cookie_info)
        elif 'paloalto' in cookie.domain or 'mycpau' in cookie.domain:
            cpau_cookies.append(cookie_info)

    print("\nCPAU Portal Cookies:")
    for c in cpau_cookies:
        print(f"  {c}")

    print("\nWatersmart.com Cookies:")
    if watersmart_cookies:
        for c in watersmart_cookies:
            print(f"  {c}")
    else:
        print("  (none)")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("-" * 70)
    print("\n1. Check /tmp/watersmart_*.html files for page content")
    print("2. Review cookies above")
    print("3. Use browser dev tools to:")
    print("   - Manually navigate from CPAU portal to watersmart.com")
    print("   - Capture the redirect chain")
    print("   - Identify API calls on the Track Usage page")
    print("4. Document findings in AUTHENTICATION_FINDINGS.md")

    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
