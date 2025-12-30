#!/usr/bin/env python3
"""
Test script for the cpau_api library.

This script tests basic functionality of the CPAU API library by fetching
a small amount of data using the library interface.
"""

import json
import sys
from datetime import date, timedelta

# Add parent directory to path to import cpau_api
sys.path.insert(0, '/Users/jsinnott/code/cpau-scrape')

from cpau_api import CpauApiSession


def main():
    # Load credentials
    with open('secrets.json', 'r') as f:
        creds = json.load(f)

    print("Testing CPAU API Library")
    print("=" * 70)

    try:
        # Create session and login
        print("\n1. Creating session and logging in...")
        with CpauApiSession(userid=creds['userid'], password=creds['password']) as session:
            print(f"   ✓ Authenticated: {session.is_authenticated}")

            # Get meter
            print("\n2. Getting electric meter...")
            meter = session.get_electric_meter()
            print(f"   ✓ Meter number: {meter.meter_number}")
            print(f"   ✓ Address: {meter.address}")
            print(f"   ✓ Rate category: {meter.rate_category}")
            print(f"   ✓ Available intervals: {', '.join(meter.get_available_intervals())}")

            # Test daily data for last week
            print("\n3. Testing get_daily_usage() for last week...")
            end_date = date.today() - timedelta(days=2)
            start_date = end_date - timedelta(days=6)
            print(f"   Date range: {start_date} to {end_date}")

            daily_data = meter.get_daily_usage(start_date, end_date)
            print(f"   ✓ Retrieved {len(daily_data)} records")

            if daily_data:
                print("\n   Sample records:")
                for record in daily_data[:3]:  # Show first 3
                    print(f"     {record.date.strftime('%Y-%m-%d')}: "
                          f"Import={record.import_kwh:.2f} kWh, "
                          f"Export={record.export_kwh:.2f} kWh, "
                          f"Net={record.net_kwh:.2f} kWh")

            # Test monthly data for current year
            print("\n4. Testing get_monthly_usage() for 2024...")
            monthly_data = meter.get_monthly_usage(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31)
            )
            print(f"   ✓ Retrieved {len(monthly_data)} billing periods")

            if monthly_data:
                print("\n   Sample records:")
                for record in monthly_data[:3]:  # Show first 3
                    print(f"     {record.billing_period}: Net={record.net_kwh:.2f} kWh")

            # Test hourly data for one day
            print("\n5. Testing get_hourly_usage() for one day...")
            test_date = end_date
            hourly_data = meter.get_hourly_usage(test_date, test_date)
            print(f"   ✓ Retrieved {len(hourly_data)} hourly records for {test_date}")

            if hourly_data:
                print("\n   Sample records:")
                for record in hourly_data[:3]:  # Show first 3
                    print(f"     {record.date}: "
                          f"Import={record.import_kwh:.2f} kWh, "
                          f"Export={record.export_kwh:.2f} kWh")

            print("\n" + "=" * 70)
            print("✓ All tests passed!")
            print("\nThe CPAU API library is working correctly.")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
