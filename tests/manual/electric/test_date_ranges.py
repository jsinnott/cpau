#!/usr/bin/env python3
"""
Test different date range formats to understand the API
"""

import json
import requests
import re
from datetime import datetime, timedelta


def test_date_formats():
    """Test what date formats the API accepts"""

    with open('../../secrets.json', 'r') as f:
        creds = json.load(f)

    # Create session and login
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })

    # Login
    print("Logging in...")
    homepage = session.get('https://mycpau.cityofpaloalto.org/Portal')
    csrf_match = re.search(r'name="__RequestVerificationToken".*?value="([^"]+)"', homepage.text)
    csrf_token = csrf_match.group(1) if csrf_match else None

    login_payload = {
        'username': creds['userid'],
        'password': creds['password'],
        'rememberme': False,
        'calledFrom': 'LN',
        'ExternalLoginId': '',
        'LoginMode': '1'
    }

    login_headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'isajax': '1',
        'Referer': 'https://mycpau.cityofpaloalto.org/Portal/',
        'csrftoken': csrf_token
    }

    session.post('https://mycpau.cityofpaloalto.org/Portal/Default.aspx/validateLogin',
                 json=login_payload, headers=login_headers)

    # Load Usages page to get CSRF token
    print("Loading Usages page...")
    usages_page = session.get('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx')

    csrf_match = re.search(r'name="ctl00\$hdnCSRFToken".*?value="([^"]+)"', usages_page.text)
    csrf_token = csrf_match.group(1) if csrf_match else None

    # Get meter info
    meter_url = 'https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/BindMultiMeter'
    usage_url = 'https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/LoadUsage'

    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://mycpau.cityofpaloalto.org/Portal/Usages.aspx',
        'csrftoken': csrf_token
    }

    meter_response = session.post(meter_url, json={'MeterType': 'E'}, headers=headers)
    meter_data = json.loads(meter_response.json()['d'])
    meter_number = None
    for meter in meter_data.get('MeterDetails', []):
        if meter['Status'] == 1:
            meter_number = meter['MeterNumber']
            break

    if not meter_number:
        print("No active meter found")
        return

    print(f"Using meter: {meter_number}")

    # Test different date formats
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)

    date_formats_to_test = [
        # Format 1: MM/DD/YY
        {'from': week_ago.strftime('%m/%d/%y'), 'to': today.strftime('%m/%d/%y')},
        # Format 2: MM/DD/YYYY
        {'from': week_ago.strftime('%m/%d/%Y'), 'to': today.strftime('%m/%d/%Y')},
        # Format 3: YYYY-MM-DD
        {'from': week_ago.strftime('%Y-%m-%d'), 'to': today.strftime('%Y-%m-%d')},
        # Format 4: M/D/YY (no leading zeros)
        {'from': week_ago.strftime('%-m/%-d/%y'), 'to': today.strftime('%-m/%-d/%y')},
    ]

    print("\n" + "="*80)
    print("Testing different date formats with Daily (D) mode...")
    print("="*80)

    for i, date_format in enumerate(date_formats_to_test, 1):
        print(f"\nTest {i}: DateFrom={date_format['from']}, DateTo={date_format['to']}")

        payload = {
            'UsageOrGeneration': '1',
            'Type': 'K',
            'Mode': 'D',  # Daily mode
            'strDate': '',
            'hourlyType': 'H',
            'SeasonId': 0,
            'weatherOverlay': 0,
            'usageyear': '',
            'MeterNumber': meter_number,
            'DateFromDaily': date_format['from'],
            'DateToDaily': date_format['to'],
            'IsTier': True,
            'IsTou': False
        }

        try:
            response = session.post(usage_url, json=payload, headers=headers)
            if response.status_code == 200:
                data = json.loads(response.json()['d'])
                if 'objUsageGenerationResultSetTwo' in data:
                    records = data['objUsageGenerationResultSetTwo']
                    print(f"  ✓ Success! Got {len(records)} records")
                    if records:
                        print(f"    First record date: {records[0].get('UsageDate', 'N/A')}")
                        print(f"    Last record date: {records[-1].get('UsageDate', 'N/A')}")
                else:
                    print(f"  ⚠ Response structure unexpected")
                    print(f"    Keys: {list(data.keys())}")
            else:
                print(f"  ✗ Failed with status {response.status_code}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

    # Also test hourly mode with date ranges
    print("\n" + "="*80)
    print("Testing with Hourly (H) mode...")
    print("="*80)

    # For hourly, try just today
    date_format = {
        'from': today.strftime('%m/%d/%y'),
        'to': today.strftime('%m/%d/%y')
    }

    print(f"\nTest: DateFrom={date_format['from']}, DateTo={date_format['to']}")

    payload = {
        'UsageOrGeneration': '1',
        'Type': 'K',
        'Mode': 'H',  # Hourly mode
        'strDate': '',
        'hourlyType': 'H',
        'SeasonId': 0,
        'weatherOverlay': 0,
        'usageyear': '',
        'MeterNumber': meter_number,
        'DateFromDaily': date_format['from'],
        'DateToDaily': date_format['to'],
        'IsTier': True,
        'IsTou': False
    }

    try:
        response = session.post(usage_url, json=payload, headers=headers)
        if response.status_code == 200:
            data = json.loads(response.json()['d'])
            if 'objUsageGenerationResultSetTwo' in data:
                records = data['objUsageGenerationResultSetTwo']
                print(f"  ✓ Success! Got {len(records)} records")
                if records:
                    print(f"    Sample record: {json.dumps(records[0], indent=4)}")
            else:
                print(f"  ⚠ Response structure unexpected")
        else:
            print(f"  ✗ Failed with status {response.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")


if __name__ == '__main__':
    test_date_formats()
