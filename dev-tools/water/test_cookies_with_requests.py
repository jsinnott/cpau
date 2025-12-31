#!/usr/bin/env python3
"""
Phase 2: Test if we can use Playwright-extracted cookies with requests library.

This tests the hybrid approach:
1. Authenticate once with Playwright (headless)
2. Extract session cookies
3. Use requests library for all subsequent API calls
"""

import json
from pathlib import Path
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright


def authenticate_and_get_cookies(username, password):
    """
    Authenticate using Playwright and return session cookies.

    Returns:
        dict: Cookie jar suitable for requests library
    """
    print("Authenticating with Playwright (headless)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Login to CPAU
        page.goto('https://mycpau.cityofpaloalto.org/Portal')
        page.fill('#txtLogin', username)
        page.fill('#txtpwd', password)
        page.press('#txtpwd', 'Enter')
        page.wait_for_load_state('networkidle')

        # Navigate to watersmart to complete SAML flow
        page.goto('https://paloalto.watersmart.com/index.php/trackUsage')
        page.wait_for_load_state('networkidle')

        # Extract cookies
        cookies = context.cookies()

        browser.close()

    print(f"✓ Authentication successful, extracted {len(cookies)} cookies\n")

    # Convert to requests-compatible format
    cookie_jar = {}
    for cookie in cookies:
        cookie_jar[cookie['name']] = cookie['value']

    return cookie_jar


def test_api_with_requests(cookies):
    """
    Test various watersmart APIs using requests library with extracted cookies.

    Args:
        cookies: Cookie dictionary from authenticate_and_get_cookies()

    Returns:
        dict: Results of API tests
    """
    print("Testing APIs with requests library...")
    print("=" * 70)

    session = requests.Session()

    # Add cookies to session
    for name, value in cookies.items():
        session.cookies.set(name, value, domain='paloalto.watersmart.com')

    # Test each API endpoint
    apis = [
        {
            'name': 'RealTimeChart',
            'url': 'https://paloalto.watersmart.com/index.php/rest/v1/Chart/RealTimeChart',
            'description': 'Hourly usage data (~3 months)'
        },
        {
            'name': 'weatherConsumptionChart',
            'url': 'https://paloalto.watersmart.com/index.php/rest/v1/Chart/weatherConsumptionChart?module=portal&commentary=full',
            'description': 'Daily usage with weather'
        },
        {
            'name': 'BillingHistoryChart',
            'url': 'https://paloalto.watersmart.com/index.php/rest/v1/Chart/BillingHistoryChart?flowType=per_day&comparison=cohort',
            'description': 'Billing period history'
        },
        {
            'name': 'yearOverYearChart',
            'url': 'https://paloalto.watersmart.com/index.php/rest/v1/Chart/yearOverYearChart?module=portal&commentary=full',
            'description': 'Monthly usage by year'
        },
        {
            'name': 'annualChart',
            'url': 'https://paloalto.watersmart.com/index.php/rest/v1/Chart/annualChart?module=portal&commentary=full',
            'description': 'Annual totals'
        },
        {
            'name': 'usagePieChart',
            'url': 'https://paloalto.watersmart.com/index.php/rest/v1/Chart/usagePieChart?module=portal&commentary=full',
            'description': 'Usage breakdown by category'
        }
    ]

    results = []

    for api in apis:
        print(f"\n{api['name']}")
        print(f"  {api['description']}")
        print(f"  URL: {api['url']}")

        try:
            response = session.get(api['url'], timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Analyze response structure
                if 'data' in data:
                    print(f"  ✓ SUCCESS (status 200)")

                    # Count data points
                    data_content = data['data']
                    if isinstance(data_content, dict):
                        if 'series' in data_content:
                            count = len(data_content['series'])
                            print(f"    Retrieved {count} data points")
                        elif 'chartData' in data_content:
                            print(f"    Chart data present")
                        else:
                            print(f"    Keys: {list(data_content.keys())[:5]}")

                    results.append({
                        'name': api['name'],
                        'status': 'success',
                        'http_status': 200,
                        'has_data': True
                    })
                else:
                    print(f"  ⚠ SUCCESS but unexpected format")
                    print(f"    Keys: {list(data.keys())}")
                    results.append({
                        'name': api['name'],
                        'status': 'success',
                        'http_status': 200,
                        'has_data': False
                    })

            elif response.status_code == 401:
                print(f"  ✗ FAILED - Not authenticated (401)")
                results.append({
                    'name': api['name'],
                    'status': 'auth_failed',
                    'http_status': 401
                })

            elif response.status_code == 403:
                print(f"  ✗ FAILED - Forbidden (403)")
                results.append({
                    'name': api['name'],
                    'status': 'forbidden',
                    'http_status': 403
                })

            else:
                print(f"  ✗ FAILED - HTTP {response.status_code}")
                results.append({
                    'name': api['name'],
                    'status': 'error',
                    'http_status': response.status_code
                })

        except requests.exceptions.RequestException as e:
            print(f"  ✗ FAILED - {type(e).__name__}: {e}")
            results.append({
                'name': api['name'],
                'status': 'exception',
                'error': str(e)
            })

    return results


def main():
    # Load credentials
    secrets_path = Path(__file__).parent.parent.parent / 'secrets.json'
    with open(secrets_path, 'r') as f:
        creds = json.load(f)

    print("\n" + "=" * 70)
    print("Phase 2: Testing Requests Library with Playwright Cookies")
    print("=" * 70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Step 1: Authenticate and get cookies
    cookies = authenticate_and_get_cookies(creds['userid'], creds['password'])

    # Step 2: Test APIs using requests library
    results = test_api_with_requests(cookies)

    # Step 3: Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] != 'success']

    print(f"\nTotal APIs tested: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

    if len(successful) == len(results):
        print("\n✓ ALL TESTS PASSED!")
        print("\nConclusion:")
        print("  - Playwright authentication works in headless mode")
        print("  - Extracted cookies work with requests library")
        print("  - All water data APIs accessible via requests")
        print("  - Hybrid approach (Playwright + requests) is viable!")
    else:
        print("\n⚠ SOME TESTS FAILED")
        print("\nFailed APIs:")
        for r in failed:
            print(f"  - {r['name']}: {r['status']}")

    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")

    return len(failed) == 0


if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
