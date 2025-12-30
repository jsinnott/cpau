#!/usr/bin/env python3
"""
Test if strDate parameter controls the date range for daily mode
"""

import json
import re
import requests

with open('../../secrets.json', 'r') as f:
    creds = json.load(f)

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

# Login
homepage = session.get('https://mycpau.cityofpaloalto.org/Portal')
csrf_match = re.search(r'name="__RequestVerificationToken".*?value="([^"]+)"', homepage.text)
csrf_token = csrf_match.group(1) if csrf_match else None

session.post('https://mycpau.cityofpaloalto.org/Portal/Default.aspx/validateLogin',
             json={'username': creds['userid'], 'password': creds['password'], 'rememberme': False,
                   'calledFrom': 'LN', 'ExternalLoginId': '', 'LoginMode': '1'},
             headers={'Content-Type': 'application/json; charset=UTF-8', 'X-Requested-With': 'XMLHttpRequest',
                     'isajax': '1', 'Referer': 'https://mycpau.cityofpaloalto.org/Portal/',
                     'csrftoken': csrf_token})

# Load Usages page
usages_page = session.get('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx')
csrf_match = re.search(r'name="ctl00\$hdnCSRFToken".*?value="([^"]+)"', usages_page.text)
csrf_token = csrf_match.group(1) if csrf_match else None

# Get meter
headers = {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest',
          'Referer': 'https://mycpau.cityofpaloalto.org/Portal/Usages.aspx', 'csrftoken': csrf_token}

meter_response = session.post('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/BindMultiMeter',
                              json={'MeterType': 'E'}, headers=headers)
meter_data = json.loads(meter_response.json()['d'])
meter_number = None
for meter in meter_data.get('MeterDetails', []):
    if meter.get('Status') == 1:
        meter_number = meter['MeterNumber']
        break

print(f"Testing with meter: {meter_number}\n")

# Test different strDate configurations
tests = [
    {
        'name': 'Test 1: strDate with single date',
        'payload': {
            'UsageOrGeneration': '1',
            'Type': 'K',
            'Mode': 'D',
            'strDate': '11/22/25',
            'hourlyType': 'H',
            'SeasonId': 0,
            'weatherOverlay': 0,
            'usageyear': '',
            'MeterNumber': meter_number,
            'DateFromDaily': '',
            'DateToDaily': '',
            'IsTier': True,
            'IsTou': False
        }
    },
    {
        'name': 'Test 2: strDate with range (from-to)',
        'payload': {
            'UsageOrGeneration': '1',
            'Type': 'K',
            'Mode': 'D',
            'strDate': '11/21/25-11/23/25',
            'hourlyType': 'H',
            'SeasonId': 0,
            'weatherOverlay': 0,
            'usageyear': '',
            'MeterNumber': meter_number,
            'DateFromDaily': '',
            'DateToDaily': '',
            'IsTier': True,
            'IsTou': False
        }
    },
    {
        'name': 'Test 3: Both strDate AND DateFromDaily/ToDaily',
        'payload': {
            'UsageOrGeneration': '1',
            'Type': 'K',
            'Mode': 'D',
            'strDate': '11/22/25',
            'hourlyType': 'H',
            'SeasonId': 0,
            'weatherOverlay': 0,
            'usageyear': '',
            'MeterNumber': meter_number,
            'DateFromDaily': '11/21/25',
            'DateToDaily': '11/23/25',
            'IsTier': True,
            'IsTou': False
        }
    },
]

for test in tests:
    print("="*80)
    print(f"{test['name']}")
    print(f"Payload: strDate='{test['payload']['strDate']}', DateFrom='{test['payload']['DateFromDaily']}', DateTo='{test['payload']['DateToDaily']}'")

    response = session.post('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/LoadUsage',
                           json=test['payload'], headers=headers)

    if response.status_code == 200:
        data = json.loads(response.json()['d'])
        records = data.get('objUsageGenerationResultSetTwo', [])

        # Get unique dates
        usage_dates = set()
        for record in records:
            if 'UsageDate' in record:
                usage_dates.add(record['UsageDate'])

        print(f"Total records: {len(records)}")
        print(f"Unique dates: {len(usage_dates)}")
        if usage_dates:
            print(f"Date range in response: {min(usage_dates)} to {max(usage_dates)}")

        if len(usage_dates) <= 10:
            print(f"All dates: {sorted(usage_dates)}")
    else:
        print(f"Error: Status {response.status_code}")

    print()
