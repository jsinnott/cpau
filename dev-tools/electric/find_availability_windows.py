#!/usr/bin/env python3
"""
Find the earliest and latest dates for which data is available for each interval type.
Uses binary search to efficiently locate the data availability window.
"""

import json
import re
import requests
from datetime import datetime, timedelta


def login_and_setup():
    """Login to CPAU and return session, headers, and meter number"""
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
    csrf_token = csrf_match.group(1)

    # Get meter
    headers = {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest',
              'Referer': 'https://mycpau.cityofpaloalto.org/Portal/Usages.aspx', 'csrftoken': csrf_token}

    meter_response = session.post('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/BindMultiMeter',
                                  json={'MeterType': 'E'}, headers=headers)
    meter_data = json.loads(meter_response.json()['d'])
    meter_number = [m['MeterNumber'] for m in meter_data['MeterDetails'] if m['Status'] == 1][0]

    return session, headers, meter_number


def check_data_exists(session, headers, meter_number, mode, date_str):
    """Check if data exists for a given date and mode"""
    payload = {
        'UsageOrGeneration': '1',
        'Type': 'K',
        'Mode': mode,
        'strDate': date_str,
        'hourlyType': 'H',
        'SeasonId': '' if mode == 'M' else 0,
        'weatherOverlay': 0,
        'usageyear': '',
        'MeterNumber': meter_number,
        'DateFromDaily': '',
        'DateToDaily': '',
        'IsTier': True,
        'IsTou': False
    }

    response = session.post('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/LoadUsage',
                           json=payload, headers=headers)

    if response.status_code == 200:
        data = json.loads(response.json()['d'])
        records = data.get('objUsageGenerationResultSetTwo', [])
        return len(records) > 0
    return False


def find_earliest_monthly(session, headers, meter_number):
    """Find earliest monthly billing period"""
    # For monthly, just get all data and find the earliest
    payload = {
        'UsageOrGeneration': '1',
        'Type': 'K',
        'Mode': 'M',
        'strDate': '',
        'hourlyType': 'H',
        'SeasonId': '',
        'weatherOverlay': 0,
        'usageyear': '',
        'MeterNumber': meter_number,
        'DateFromDaily': '',
        'DateToDaily': '',
        'IsTier': True,
        'IsTou': False
    }

    response = session.post('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/LoadUsage',
                           json=payload, headers=headers)

    if response.status_code == 200:
        data = json.loads(response.json()['d'])
        records = data.get('objUsageGenerationResultSetTwo', [])

        # Find earliest billing period
        earliest_period = None
        for record in records:
            bill_period = record.get('BillPeriod', '')
            if ' to ' in bill_period:
                start_str = bill_period.split(' to ')[0].strip()
                try:
                    start_date = datetime.strptime(start_str, '%m/%d/%y')
                    if earliest_period is None or start_date < earliest_period:
                        earliest_period = start_date
                except ValueError:
                    pass

        return earliest_period
    return None


def find_latest_monthly(session, headers, meter_number):
    """Find latest monthly billing period"""
    # For monthly, just get all data and find the latest
    payload = {
        'UsageOrGeneration': '1',
        'Type': 'K',
        'Mode': 'M',
        'strDate': '',
        'hourlyType': 'H',
        'SeasonId': '',
        'weatherOverlay': 0,
        'usageyear': '',
        'MeterNumber': meter_number,
        'DateFromDaily': '',
        'DateToDaily': '',
        'IsTier': True,
        'IsTou': False
    }

    response = session.post('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/LoadUsage',
                           json=payload, headers=headers)

    if response.status_code == 200:
        data = json.loads(response.json()['d'])
        records = data.get('objUsageGenerationResultSetTwo', [])

        # Find latest billing period
        latest_period = None
        for record in records:
            bill_period = record.get('BillPeriod', '')
            if ' to ' in bill_period:
                end_str = bill_period.split(' to ')[1].strip()
                try:
                    end_date = datetime.strptime(end_str, '%m/%d/%y')
                    if latest_period is None or end_date > latest_period:
                        latest_period = end_date
                except ValueError:
                    pass

        return latest_period
    return None


def binary_search_earliest(session, headers, meter_number, mode, mode_name):
    """Use binary search to find earliest date with data"""
    # Search range: 10 years ago to 2 days ago
    today = datetime.now()
    min_date = today - timedelta(days=3650)  # 10 years ago
    max_date = today - timedelta(days=2)     # 2 days ago (data availability)

    print(f"Searching for earliest {mode_name} data...")

    # Binary search
    left = min_date
    right = max_date
    earliest_found = None

    iterations = 0
    while left <= right:
        iterations += 1
        mid = left + (right - left) // 2
        mid_str = mid.strftime('%m/%d/%y')

        has_data = check_data_exists(session, headers, meter_number, mode, mid_str)

        if has_data:
            # Data exists, search earlier
            earliest_found = mid
            right = mid - timedelta(days=1)
        else:
            # No data, search later
            left = mid + timedelta(days=1)

    print(f"  Binary search completed in {iterations} iterations")
    return earliest_found


def binary_search_latest(session, headers, meter_number, mode, mode_name):
    """Use binary search to find latest date with data"""
    # Search range: 30 days ago to tomorrow (to handle processing delays and test for near-real-time)
    today = datetime.now()
    min_date = today - timedelta(days=30)  # Start far enough back to catch any delays
    max_date = today + timedelta(days=1)   # Check if data is near-real-time

    print(f"Searching for latest {mode_name} data...")

    # Binary search
    left = min_date
    right = max_date
    latest_found = None

    iterations = 0
    while left <= right:
        iterations += 1
        mid = left + (right - left) // 2
        mid_str = mid.strftime('%m/%d/%y')

        has_data = check_data_exists(session, headers, meter_number, mode, mid_str)

        if has_data:
            # Data exists, search later
            latest_found = mid
            left = mid + timedelta(days=1)
        else:
            # No data, search earlier
            right = mid - timedelta(days=1)

    print(f"  Binary search completed in {iterations} iterations")
    return latest_found


def main():
    print("Finding data availability window for each interval type...")
    print("=" * 70)

    session, headers, meter_number = login_and_setup()
    print(f"Connected to CPAU (meter: {meter_number})\n")

    # Monthly data
    print("MONTHLY DATA:")
    earliest_monthly = find_earliest_monthly(session, headers, meter_number)
    latest_monthly = find_latest_monthly(session, headers, meter_number)
    if earliest_monthly:
        print(f"  Earliest billing period starts: {earliest_monthly.strftime('%Y-%m-%d')}")
    if latest_monthly:
        print(f"  Latest billing period ends:     {latest_monthly.strftime('%Y-%m-%d')}")
    if not earliest_monthly and not latest_monthly:
        print("  No monthly data found")
    print()

    # Daily data
    print("DAILY DATA:")
    earliest_daily = binary_search_earliest(session, headers, meter_number, 'D', 'daily')
    if earliest_daily:
        print(f"  Earliest available date: {earliest_daily.strftime('%Y-%m-%d')}")
    latest_daily = binary_search_latest(session, headers, meter_number, 'D', 'daily')
    if latest_daily:
        print(f"  Latest available date:   {latest_daily.strftime('%Y-%m-%d')}")
    if not earliest_daily and not latest_daily:
        print("  No daily data found")
    print()

    # Hourly data
    print("HOURLY DATA:")
    earliest_hourly = binary_search_earliest(session, headers, meter_number, 'H', 'hourly')
    if earliest_hourly:
        print(f"  Earliest available date: {earliest_hourly.strftime('%Y-%m-%d')}")
    latest_hourly = binary_search_latest(session, headers, meter_number, 'H', 'hourly')
    if latest_hourly:
        print(f"  Latest available date:   {latest_hourly.strftime('%Y-%m-%d')}")
    if not earliest_hourly and not latest_hourly:
        print("  No hourly data found")
    print()

    # 15-minute data
    print("15-MINUTE DATA:")
    earliest_15min = binary_search_earliest(session, headers, meter_number, 'MI', '15-minute')
    if earliest_15min:
        print(f"  Earliest available date: {earliest_15min.strftime('%Y-%m-%d')}")
    latest_15min = binary_search_latest(session, headers, meter_number, 'MI', '15-minute')
    if latest_15min:
        print(f"  Latest available date:   {latest_15min.strftime('%Y-%m-%d')}")
    if not earliest_15min and not latest_15min:
        print("  No 15-minute data found")
    print()

    # Summary
    print("=" * 70)
    print("SUMMARY:")
    if earliest_monthly or latest_monthly:
        earliest_str = earliest_monthly.strftime('%Y-%m-%d') if earliest_monthly else 'unknown'
        latest_str = latest_monthly.strftime('%Y-%m-%d') if latest_monthly else 'unknown'
        print(f"  Monthly:    {earliest_str} to {latest_str}")
    if earliest_daily or latest_daily:
        earliest_str = earliest_daily.strftime('%Y-%m-%d') if earliest_daily else 'unknown'
        latest_str = latest_daily.strftime('%Y-%m-%d') if latest_daily else 'unknown'
        print(f"  Daily:      {earliest_str} to {latest_str}")
    if earliest_hourly or latest_hourly:
        earliest_str = earliest_hourly.strftime('%Y-%m-%d') if earliest_hourly else 'unknown'
        latest_str = latest_hourly.strftime('%Y-%m-%d') if latest_hourly else 'unknown'
        print(f"  Hourly:     {earliest_str} to {latest_str}")
    if earliest_15min or latest_15min:
        earliest_str = earliest_15min.strftime('%Y-%m-%d') if earliest_15min else 'unknown'
        latest_str = latest_15min.strftime('%Y-%m-%d') if latest_15min else 'unknown'
        print(f"  15-minute:  {earliest_str} to {latest_str}")


if __name__ == '__main__':
    main()
