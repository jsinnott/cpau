#!/usr/bin/env python3
"""
Test what data is available for different intervals and dates
"""

import json
import re
import requests
from datetime import datetime, timedelta

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

print(f"Testing data availability for meter: {meter_number}")
print("="*80)

# Test different dates for different intervals
today = datetime.now()
dates_to_test = [
    ('Today', today),
    ('Yesterday', today - timedelta(days=1)),
    ('2 days ago', today - timedelta(days=2)),
    ('3 days ago', today - timedelta(days=3)),
    ('7 days ago', today - timedelta(days=7)),
]

intervals = [
    ('Daily', 'D'),
    ('Hourly', 'H'),
    ('15-min', 'MI'),
]

print("\nData Availability Matrix:")
print(f"{'Date':<15} {'Daily':<10} {'Hourly':<10} {'15-min':<10}")
print("-" * 50)

for date_label, date_obj in dates_to_test:
    date_str = date_obj.strftime('%m/%d/%y')
    results = []

    for interval_label, mode in intervals:
        payload = {
            'UsageOrGeneration': '1',
            'Type': 'K',
            'Mode': mode,
            'strDate': '',
            'hourlyType': 'H',
            'SeasonId': 0,
            'weatherOverlay': 0,
            'usageyear': '',
            'MeterNumber': meter_number,
            'DateFromDaily': date_str,
            'DateToDaily': date_str,
            'IsTier': True,
            'IsTou': False
        }

        response = session.post('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/LoadUsage',
                               json=payload, headers=headers)
        data = json.loads(response.json()['d'])
        record_count = len(data.get('objUsageGenerationResultSetTwo', []))
        results.append(f"{record_count} recs" if record_count > 0 else "-")

    print(f"{date_label:<15} {results[0]:<10} {results[1]:<10} {results[2]:<10}")

# Let's also try an older date to see if granular data exists
print("\n" + "="*80)
print("Detailed test for 3 days ago...")
date_3_days = (today - timedelta(days=3)).strftime('%m/%d/%y')

for interval_label, mode in [('Hourly', 'H'), ('15-min', 'MI')]:
    payload = {
        'UsageOrGeneration': '1',
        'Type': 'K',
        'Mode': mode,
        'strDate': '',
        'hourlyType': 'H',
        'SeasonId': 0,
        'weatherOverlay': 0,
        'usageyear': '',
        'MeterNumber': meter_number,
        'DateFromDaily': date_3_days,
        'DateToDaily': date_3_days,
        'IsTier': True,
        'IsTou': False
    }

    response = session.post('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/LoadUsage',
                           json=payload, headers=headers)
    data = json.loads(response.json()['d'])
    records = data.get('objUsageGenerationResultSetTwo', [])

    print(f"\n{interval_label} for {date_3_days}: {len(records)} records")
    if records:
        print(f"  First record keys: {list(records[0].keys())}")
        print(f"  Sample record:")
        for key in ['UsageDate', 'Hourly', 'UsageType', 'UsageValue', 'DemandValue']:
            print(f"    {key}: {records[0].get(key)}")
