#!/usr/bin/env python3
"""
Quick script to inspect what fields are returned for daily data
"""

import json
import sys
import re
import requests
from datetime import datetime

with open('../../secrets.json', 'r') as f:
    creds = json.load(f)

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
})

# Login
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

# Load Usages page
usages_page = session.get('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx')
csrf_match = re.search(r'name="ctl00\$hdnCSRFToken".*?value="([^"]+)"', usages_page.text)
csrf_token = csrf_match.group(1) if csrf_match else None

# Get meter
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
meter_number = meter_data['MeterDetails'][0]['MeterNumber']

# Get daily data
payload = {
    'UsageOrGeneration': '1',
    'Type': 'K',
    'Mode': 'D',
    'strDate': '',
    'hourlyType': 'H',
    'SeasonId': 0,
    'weatherOverlay': 0,
    'usageyear': '',
    'MeterNumber': meter_number,
    'DateFromDaily': '12/15/25',
    'DateToDaily': '12/20/25',
    'IsTier': True,
    'IsTou': False
}

response = session.post(usage_url, json=payload, headers=headers)
data = json.loads(response.json()['d'])

print("DAILY DATA STRUCTURE")
print("="*80)
print("\nTop-level keys:")
for key in data.keys():
    print(f"  - {key}")

if 'objUsageGenerationResultSetTwo' in data:
    records = data['objUsageGenerationResultSetTwo']
    print(f"\nTotal records: {len(records)}")

    if records:
        print("\nFirst record:")
        print(json.dumps(records[0], indent=2))

        print("\nAll keys in first record:")
        for key in sorted(records[0].keys()):
            print(f"  - {key}: {records[0][key]}")
