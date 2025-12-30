#!/usr/bin/env python3
"""
Test date parameters for hourly and 15-minute modes
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

# Test hourly mode
print("="*80)
print("HOURLY MODE (H)")
print("="*80)

tests = [
    {
        'name': 'H1: DateFrom=DateTo (single day)',
        'mode': 'H',
        'DateFromDaily': '12/17/25',
        'DateToDaily': '12/17/25',
        'strDate': ''
    },
    {
        'name': 'H2: DateFrom != DateTo (3-day range)',
        'mode': 'H',
        'DateFromDaily': '12/17/25',
        'DateToDaily': '12/19/25',
        'strDate': ''
    },
    {
        'name': 'H3: strDate only',
        'mode': 'H',
        'DateFromDaily': '',
        'DateToDaily': '',
        'strDate': '12/17/25'
    },
]

for test in tests:
    print(f"\n{test['name']}")
    print(f"  strDate='{test['strDate']}', DateFrom='{test['DateFromDaily']}', DateTo='{test['DateToDaily']}'")

    payload = {
        'UsageOrGeneration': '1',
        'Type': 'K',
        'Mode': test['mode'],
        'strDate': test['strDate'],
        'hourlyType': 'H',
        'SeasonId': 0,
        'weatherOverlay': 0,
        'usageyear': '',
        'MeterNumber': meter_number,
        'DateFromDaily': test['DateFromDaily'],
        'DateToDaily': test['DateToDaily'],
        'IsTier': True,
        'IsTou': False
    }

    response = session.post('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/LoadUsage',
                           json=payload, headers=headers)

    if response.status_code == 200:
        data = json.loads(response.json()['d'])
        records = data.get('objUsageGenerationResultSetTwo', [])

        # Get unique dates
        usage_dates = set()
        for record in records:
            if 'UsageDate' in record:
                usage_dates.add(record['UsageDate'])

        print(f"  Records: {len(records)}, Unique dates: {len(usage_dates)}")
        if usage_dates:
            sorted_dates = sorted(usage_dates)
            print(f"  Date range: {sorted_dates[0]} to {sorted_dates[-1]}")
            if len(sorted_dates) <= 5:
                print(f"  All dates: {sorted_dates}")

# Test 15-minute mode
print("\n" + "="*80)
print("15-MINUTE MODE (MI)")
print("="*80)

tests_15min = [
    {
        'name': 'MI1: DateFrom=DateTo (single day)',
        'DateFromDaily': '12/17/25',
        'DateToDaily': '12/17/25',
        'strDate': ''
    },
    {
        'name': 'MI2: DateFrom != DateTo (3-day range)',
        'DateFromDaily': '12/17/25',
        'DateToDaily': '12/19/25',
        'strDate': ''
    },
]

for test in tests_15min:
    print(f"\n{test['name']}")
    print(f"  strDate='{test['strDate']}', DateFrom='{test['DateFromDaily']}', DateTo='{test['DateToDaily']}'")

    payload = {
        'UsageOrGeneration': '1',
        'Type': 'K',
        'Mode': 'MI',
        'strDate': test['strDate'],
        'hourlyType': 'H',
        'SeasonId': 0,
        'weatherOverlay': 0,
        'usageyear': '',
        'MeterNumber': meter_number,
        'DateFromDaily': test['DateFromDaily'],
        'DateToDaily': test['DateToDaily'],
        'IsTier': True,
        'IsTou': False
    }

    response = session.post('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/LoadUsage',
                           json=payload, headers=headers)

    if response.status_code == 200:
        data = json.loads(response.json()['d'])
        records = data.get('objUsageGenerationResultSetTwo', [])

        # Get unique dates
        usage_dates = set()
        for record in records:
            if 'UsageDate' in record:
                usage_dates.add(record['UsageDate'])

        print(f"  Records: {len(records)}, Unique dates: {len(usage_dates)}")
        if usage_dates:
            sorted_dates = sorted(usage_dates)
            print(f"  Date range: {sorted_dates[0]} to {sorted_dates[-1]}")
            if len(sorted_dates) <= 5:
                print(f"  All dates: {sorted_dates}")
