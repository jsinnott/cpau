#!/usr/bin/env python3
"""
Check what hourly data looks like
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

meter_data = json.loads(session.post('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/BindMultiMeter',
                                     json={'MeterType': 'E'}, headers=headers).json()['d'])
meter_number = meter_data['MeterDetails'][0]['MeterNumber']

# Try hourly with empty dates (default)
payload = {'UsageOrGeneration': '1', 'Type': 'K', 'Mode': 'H', 'strDate': '', 'hourlyType': 'H',
          'SeasonId': 0, 'weatherOverlay': 0, 'usageyear': '', 'MeterNumber': meter_number,
          'DateFromDaily': '', 'DateToDaily': '', 'IsTier': True, 'IsTou': False}

print("Test 1: Hourly with empty dates")
response = session.post('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/LoadUsage',
                       json=payload, headers=headers)
data = json.loads(response.json()['d'])
print(f"Records: {len(data.get('objUsageGenerationResultSetTwo', []))}")
if data.get('objUsageGenerationResultSetTwo'):
    print(f"First record: {json.dumps(data['objUsageGenerationResultSetTwo'][0], indent=2)}")

# Try with specific date (today)
from datetime import datetime
today = datetime.now().strftime('%m/%d/%y')
payload['DateFromDaily'] = today
payload['DateToDaily'] = today

print(f"\nTest 2: Hourly with date {today}")
response = session.post('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/LoadUsage',
                       json=payload, headers=headers)
data = json.loads(response.json()['d'])
print(f"Records: {len(data.get('objUsageGenerationResultSetTwo', []))}")
if data.get('objUsageGenerationResultSetTwo'):
    print(f"First record: {json.dumps(data['objUsageGenerationResultSetTwo'][0], indent=2)}")
