"""
Command-line interface for CPAU API tools.

This module provides CLI entry points for the cpau-electric and future
cpau-water commands.
"""

import json
import sys
import csv
from argparse import ArgumentParser
from datetime import date, timedelta
from pathlib import Path

from .session import CpauApiSession
from .exceptions import CpauError


def main_electric():
    """Entry point for cpau-electric command."""
    parser = ArgumentParser(
        description="Download electric meter data from City of Palo Alto Utilities"
    )

    parser.add_argument(
        '-i',
        '--interval',
        type=str,
        choices=['monthly', 'daily', 'hourly', '15min'],
        default='monthly',
        help='Time interval for data retrieval (default: monthly)'
    )

    parser.add_argument(
        '-o',
        '--output-file',
        type=str,
        default=None,
        help='Path to output file (default: stdout)'
    )

    parser.add_argument(
        '--secrets-file',
        type=str,
        default='secrets.json',
        help='Path to JSON file containing CPAU login credentials (default: secrets.json)'
    )

    parser.add_argument(
        'start_date',
        type=str,
        help='Start date for data retrieval in YYYY-MM-DD format (e.g., 2025-12-01)'
    )

    parser.add_argument(
        'end_date',
        type=str,
        nargs='?',
        default=None,
        help='End date for data retrieval in YYYY-MM-DD format (default: 2 days ago)'
    )

    args = parser.parse_args()

    # Parse dates
    try:
        start_date_obj = date.fromisoformat(args.start_date)
    except ValueError:
        print(f"Error: Invalid start date format: {args.start_date} (expected YYYY-MM-DD)", file=sys.stderr)
        return 1

    if args.end_date:
        try:
            end_date_obj = date.fromisoformat(args.end_date)
        except ValueError:
            print(f"Error: Invalid end date format: {args.end_date} (expected YYYY-MM-DD)", file=sys.stderr)
            return 1
    else:
        end_date_obj = date.today() - timedelta(days=2)

    # Load credentials
    try:
        secrets_path = Path(args.secrets_file)
        if not secrets_path.exists():
            print(f"Error: Secrets file not found: {args.secrets_file}", file=sys.stderr)
            print(f"Please create a JSON file with 'userid' and 'password' fields.", file=sys.stderr)
            return 1

        with open(secrets_path, 'r') as f:
            creds = json.load(f)

        if 'userid' not in creds or 'password' not in creds:
            print(f"Error: Secrets file must contain 'userid' and 'password' fields", file=sys.stderr)
            return 1

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in secrets file: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: Failed to read secrets file: {e}", file=sys.stderr)
        return 1

    # Fetch data using the API
    try:
        with CpauApiSession(userid=creds['userid'], password=creds['password']) as session:
            # Get meter
            meter = session.get_electric_meter()

            # Get usage data
            usage_records = meter.get_usage(
                interval=args.interval,
                start_date=start_date_obj,
                end_date=end_date_obj
            )

            # Determine fieldnames based on interval type
            if args.interval == 'monthly':
                fieldnames = ['date', 'billing_period', 'export_kwh', 'import_kwh', 'net_kwh']
            else:
                fieldnames = ['date', 'export_kwh', 'import_kwh', 'net_kwh']

            # Convert UsageRecord objects to dicts for CSV output
            rows = []
            for record in usage_records:
                row = {
                    'date': record.date.isoformat() if args.interval in ['hourly', '15min'] else record.date.strftime('%Y-%m-%d'),
                    'export_kwh': record.export_kwh,
                    'import_kwh': record.import_kwh,
                    'net_kwh': record.net_kwh,
                }
                if args.interval == 'monthly' and record.billing_period:
                    row['billing_period'] = record.billing_period
                rows.append(row)

            # Write CSV output
            if args.output_file:
                try:
                    with open(args.output_file, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                        writer.writeheader()
                        writer.writerows(rows)
                    print(f"Wrote {len(rows)} records to {args.output_file}", file=sys.stderr)
                except Exception as e:
                    print(f"Error: Failed to write output file: {e}", file=sys.stderr)
                    return 1
            else:
                # Write to stdout
                writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(rows)

            return 0

    except CpauError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main_electric())
