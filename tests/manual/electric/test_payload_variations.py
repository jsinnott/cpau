#!/usr/bin/env python3
"""
Test different payload variations to find what works for hourly/15-minute data
"""

import json
import re
import requests
from datetime import datetime

with open('../../secrets.json', 'r') as f:
    creds = json.load(f)

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

# Login
print("Logging in...")
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

if not csrf_token:
    print("Failed to extract CSRF token from Usages page")
    exit(1)

# Get meter
headers = {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest',
          'Referer': 'https://mycpau.cityofpaloalto.org/Portal/Usages.aspx', 'csrftoken': csrf_token}

meter_response = session.post('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/BindMultiMeter',
                              json={'MeterType': 'E'}, headers=headers)
meter_data = json.loads(meter_response.json()['d'])

# Find active meter
meter_number = None
for meter in meter_data.get('MeterDetails', []):
    if meter.get('Status') == 1:
        meter_number = meter['MeterNumber']
        break

if not meter_number:
    print("Could not find active meter")
    print(f"Meter data: {json.dumps(meter_data, indent=2)}")
    exit(1)

print(f"Using meter: {meter_number}")
print("="*80)

# Test date: December 17, 2025
test_date = '12/17/25'

# Base payload that we know works for daily
base_payload = {
    'UsageOrGeneration': '1',
    'Type': 'K',
    'strDate': '',
    'hourlyType': 'H',
    'SeasonId': 0,
    'weatherOverlay': 0,
    'usageyear': '',
    'MeterNumber': meter_number,
    'IsTier': True,
    'IsTou': False
}

# Try different variations for 15-minute mode
variations = [
    {
        'name': 'Variation 1: MI mode with date range',
        'payload': {**base_payload, 'Mode': 'MI', 'DateFromDaily': test_date, 'DateToDaily': test_date}
    },
    {
        'name': 'Variation 2: MI mode with strDate',
        'payload': {**base_payload, 'Mode': 'MI', 'strDate': test_date, 'DateFromDaily': '', 'DateToDaily': ''}
    },
    {
        'name': 'Variation 3: MI mode with both strDate and DateFrom/To',
        'payload': {**base_payload, 'Mode': 'MI', 'strDate': test_date, 'DateFromDaily': test_date, 'DateToDaily': test_date}
    },
    {
        'name': 'Variation 4: MI mode with usageyear',
        'payload': {**base_payload, 'Mode': 'MI', 'DateFromDaily': test_date, 'DateToDaily': test_date, 'usageyear': '2025'}
    },
    {
        'name': 'Variation 5: MI mode with SeasonId empty string',
        'payload': {**base_payload, 'Mode': 'MI', 'DateFromDaily': test_date, 'DateToDaily': test_date, 'SeasonId': ''}
    },
    {
        'name': 'Variation 6: H mode (hourly) with date range',
        'payload': {**base_payload, 'Mode': 'H', 'DateFromDaily': test_date, 'DateToDaily': test_date}
    },
    {
        'name': 'Variation 7: H mode with strDate',
        'payload': {**base_payload, 'Mode': 'H', 'strDate': test_date, 'DateFromDaily': '', 'DateToDaily': ''}
    },
]

for variation in variations:
    print(f"\nTesting: {variation['name']}")
    print(f"Payload: {json.dumps(variation['payload'], indent=2)}")

    response = session.post('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/LoadUsage',
                           json=variation['payload'], headers=headers)

    if response.status_code == 200:
        data = json.loads(response.json()['d'])
        records = data.get('objUsageGenerationResultSetTwo', [])
        print(f"✓ Status 200 - Records: {len(records)}")

        if records:
            print(f"  SUCCESS! First record:")
            print(f"    {json.dumps(records[0], indent=4)}")
            print(f"\n  WINNING PAYLOAD:")
            print(f"  {json.dumps(variation['payload'], indent=2)}")
            break
    else:
        print(f"✗ Status {response.status_code}")

print("\n" + "="*80)
