#!/usr/bin/env python3
"""
Phase 2: Test session cookie lifetime.

This script:
1. Authenticates and extracts cookies
2. Tests API access immediately
3. Waits various intervals and retests
4. Determines how long cookies remain valid
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
import requests
from playwright.sync_api import sync_playwright


def authenticate_and_save_cookies(username, password):
    """Authenticate and save cookies to file."""
    print("Authenticating with Playwright...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto('https://mycpau.cityofpaloalto.org/Portal')
        page.fill('#txtLogin', username)
        page.fill('#txtpwd', password)
        page.press('#txtpwd', 'Enter')
        page.wait_for_load_state('networkidle')

        page.goto('https://paloalto.watersmart.com/index.php/trackUsage')
        page.wait_for_load_state('networkidle')

        cookies = context.cookies()
        browser.close()

    # Save cookies with timestamp
    cookie_data = {
        'timestamp': datetime.now().isoformat(),
        'cookies': [
            {
                'name': c['name'],
                'value': c['value'],
                'domain': c['domain'],
                'path': c['path'],
                'expires': c.get('expires', -1)
            }
            for c in cookies
        ]
    }

    cookie_file = Path('/tmp/watersmart_cookies.json')
    with open(cookie_file, 'w') as f:
        json.dump(cookie_data, f, indent=2)

    print(f"✓ Saved {len(cookies)} cookies to {cookie_file}")

    # Analyze expiration times
    watersmart_cookies = [c for c in cookie_data['cookies'] if 'watersmart' in c['domain']]
    print(f"\nWatersmart session cookies:")
    for cookie in watersmart_cookies:
        print(f"  {cookie['name']}:")
        if cookie['expires'] > 0:
            expires_dt = datetime.fromtimestamp(cookie['expires'])
            duration = expires_dt - datetime.now()
            print(f"    Expires: {expires_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    Duration: {duration}")
        else:
            print(f"    Expires: Session cookie (browser close)")

    return cookie_data


def load_cookies():
    """Load cookies from file."""
    cookie_file = Path('/tmp/watersmart_cookies.json')
    with open(cookie_file, 'r') as f:
        return json.load(f)


def test_api_with_cookies(cookie_data):
    """Test if API works with stored cookies."""
    session = requests.Session()

    for cookie in cookie_data['cookies']:
        session.cookies.set(
            cookie['name'],
            cookie['value'],
            domain=cookie['domain'],
            path=cookie['path']
        )

    # Test RealTimeChart API
    try:
        response = session.get(
            'https://paloalto.watersmart.com/index.php/rest/v1/Chart/RealTimeChart',
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'series' in data['data']:
                count = len(data['data']['series'])
                return True, f"Success - {count} data points"
        elif response.status_code == 401:
            return False, "Authentication failed (401)"
        elif response.status_code == 403:
            return False, "Forbidden (403)"
        else:
            return False, f"HTTP {response.status_code}"

    except Exception as e:
        return False, f"Exception: {e}"

    return False, "Unknown error"


def run_lifetime_test(intervals_seconds):
    """
    Test cookie lifetime by checking API access at various intervals.

    Args:
        intervals_seconds: List of seconds to wait before each test
    """
    # Load credentials
    secrets_path = Path(__file__).parent.parent.parent / 'secrets.json'
    with open(secrets_path, 'r') as f:
        creds = json.load(f)

    print("\n" + "=" * 70)
    print("Cookie Lifetime Test")
    print("=" * 70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Authenticate and save cookies
    cookie_data = authenticate_and_save_cookies(creds['userid'], creds['password'])
    auth_time = datetime.fromisoformat(cookie_data['timestamp'])

    print("\n" + "=" * 70)
    print("Testing API access at intervals...")
    print("=" * 70)

    results = []

    for interval in intervals_seconds:
        if interval > 0:
            print(f"\nWaiting {interval} seconds...")
            time.sleep(interval)

        # Reload cookies from file (simulates new process)
        cookie_data = load_cookies()
        elapsed = (datetime.now() - auth_time).total_seconds()

        print(f"\nTest at {int(elapsed)}s after authentication:")
        success, message = test_api_with_cookies(cookie_data)

        status = "✓ VALID" if success else "✗ EXPIRED/INVALID"
        print(f"  {status} - {message}")

        results.append({
            'elapsed_seconds': int(elapsed),
            'valid': success,
            'message': message
        })

        if not success:
            print("\n⚠ Cookies no longer valid - stopping test")
            break

    # Summary
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    print("\nCookie validity timeline:")
    for r in results:
        status = "✓" if r['valid'] else "✗"
        print(f"  {status} After {r['elapsed_seconds']:5d}s: {r['message']}")

    # Determine lifetime
    valid_results = [r for r in results if r['valid']]
    if valid_results:
        max_valid = max(r['elapsed_seconds'] for r in valid_results)
        print(f"\nMinimum cookie lifetime: {max_valid} seconds ({max_valid/60:.1f} minutes)")

        if len(results) > len(valid_results):
            # We found expiration
            first_invalid = [r for r in results if not r['valid']][0]
            print(f"Cookies expired between {max_valid}s and {first_invalid['elapsed_seconds']}s")
        else:
            print(f"Cookies still valid after {max_valid}s - may last longer")
    else:
        print("\n⚠ Cookies invalid immediately after authentication")

    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


def quick_test():
    """Quick test at short intervals (for development)."""
    print("\nRunning QUICK test (short intervals)...")
    print("Testing: immediately, 1min, 5min, 10min")
    run_lifetime_test([0, 60, 240, 300])  # 0s, 1min, 5min, 10min


def full_test():
    """Full test to find actual expiration (may take hours)."""
    print("\nRunning FULL test (long intervals)...")
    print("Testing: 0, 5min, 15min, 30min, 1hr, 2hr, 4hr, 8hr, 12hr, 24hr")
    run_lifetime_test([
        0,          # Immediate
        300,        # 5 minutes
        600,        # 10 more (15 min total)
        900,        # 15 more (30 min total)
        1800,       # 30 more (1 hour total)
        3600,       # 1 hour more (2 hours total)
        7200,       # 2 hours more (4 hours total)
        14400,      # 4 hours more (8 hours total)
        14400,      # 4 hours more (12 hours total)
        43200,      # 12 hours more (24 hours total)
    ])


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--full':
        full_test()
    else:
        quick_test()

    print("\nNote: For production use, cookies should be refreshed when:")
    print("  1. API returns 401 (unauthorized)")
    print("  2. Before expiration time (if known)")
    print("  3. On application startup (if cookies older than threshold)")
