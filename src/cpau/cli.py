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

from .baseapp import BaseApp
from .session import CpauApiSession
from .water_meter import CpauWaterMeter
from .exceptions import CpauError


class CpauElectricCli(BaseApp):
    """Command-line application for downloading CPAU electric meter data."""

    def add_arg_definitions(self, parser: ArgumentParser) -> None:
        """Add argument definitions to the parser."""
        # Add BaseApp's standard arguments (--verbose, --silent)
        super().add_arg_definitions(parser)

        parser.add_argument(
            '-i',
            '--interval',
            type=str,
            choices=['billing', 'monthly', 'daily', 'hourly', '15min'],
            default='billing',
            help='Time interval for data retrieval (default: billing)'
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

    def go(self, argv: list) -> int:
        """Main execution method."""
        # Parse arguments and set up logger (BaseApp infrastructure)
        super().go(argv)

        # Parse dates
        try:
            start_date_obj = date.fromisoformat(self.args.start_date)
        except ValueError:
            self.logger.error(f"Invalid start date format: {self.args.start_date} (expected YYYY-MM-DD)")
            return 1

        if self.args.end_date:
            try:
                end_date_obj = date.fromisoformat(self.args.end_date)
            except ValueError:
                self.logger.error(f"Invalid end date format: {self.args.end_date} (expected YYYY-MM-DD)")
                return 1
        else:
            end_date_obj = date.today() - timedelta(days=2)

        # Load credentials
        try:
            secrets_path = Path(self.args.secrets_file)
            if not secrets_path.exists():
                self.logger.error(f"Secrets file not found: {self.args.secrets_file}")
                self.logger.error("Please create a JSON file with 'userid' and 'password' fields.")
                return 1

            with open(secrets_path, 'r') as f:
                creds = json.load(f)

            if 'userid' not in creds or 'password' not in creds:
                self.logger.error("Secrets file must contain 'userid' and 'password' fields")
                return 1

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in secrets file: {e}")
            return 1
        except Exception as e:
            self.logger.error(f"Failed to read secrets file: {e}")
            return 1

        # Fetch data using the API
        try:
            self.logger.info("Connecting to CPAU portal")
            with CpauApiSession(userid=creds['userid'], password=creds['password']) as session:
                # Get meter
                self.logger.info("Retrieving meter information")
                meter = session.get_electric_meter()
                self.logger.debug(f"Found meter: {meter.meter_number}")

                # Get usage data
                self.logger.info(f"Fetching {self.args.interval} data from {start_date_obj} to {end_date_obj}")
                usage_records = meter.get_usage(
                    interval=self.args.interval,
                    start_date=start_date_obj,
                    end_date=end_date_obj
                )

                self.logger.info(f"Retrieved {len(usage_records)} records")

                # Determine fieldnames based on interval type
                if self.args.interval == 'billing':
                    fieldnames = ['date', 'billing_period_start', 'billing_period_end', 'billing_period_length', 'export_kwh', 'import_kwh', 'net_kwh']
                else:
                    fieldnames = ['date', 'export_kwh', 'import_kwh', 'net_kwh']

                # Convert UsageRecord objects to dicts for CSV output
                rows = []
                for record in usage_records:
                    row = {
                        'date': record.date.isoformat() if self.args.interval in ['hourly', '15min'] else record.date.strftime('%Y-%m-%d'),
                        'export_kwh': record.export_kwh,
                        'import_kwh': record.import_kwh,
                        'net_kwh': record.net_kwh,
                    }
                    if self.args.interval == 'billing':
                        row['billing_period_start'] = record.billing_period_start
                        row['billing_period_end'] = record.billing_period_end
                        row['billing_period_length'] = record.billing_period_length
                    rows.append(row)

                # Write CSV output
                if self.args.output_file:
                    try:
                        with open(self.args.output_file, 'w', newline='') as f:
                            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                            writer.writeheader()
                            writer.writerows(rows)
                        self.logger.info(f"Wrote {len(rows)} records to {self.args.output_file}")
                    except Exception as e:
                        self.logger.error(f"Failed to write output file: {e}")
                        return 1
                else:
                    # Write to stdout
                    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    writer.writerows(rows)

                return 0

        except CpauError as e:
            self.logger.error(f"CPAU API error: {e}")
            return 1
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            if self.args.verbose:
                import traceback
                traceback.print_exc()
            return 1


def main_electric():
    """Entry point for cpau-electric command."""
    app = CpauElectricCli()
    return app.go(sys.argv[1:])


class CpauWaterCli(BaseApp):
    """Command-line application for downloading CPAU water meter data."""

    def add_arg_definitions(self, parser: ArgumentParser) -> None:
        """Add argument definitions to the parser."""
        # Add BaseApp's standard arguments (--verbose, --silent)
        super().add_arg_definitions(parser)

        parser.add_argument(
            '-i',
            '--interval',
            type=str,
            choices=['billing', 'monthly', 'daily', 'hourly'],
            default='billing',
            help='Time interval for data retrieval (default: billing)'
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
            help='Start date for data retrieval in YYYY-MM-DD format (e.g., 2024-12-01)'
        )

        parser.add_argument(
            'end_date',
            type=str,
            nargs='?',
            default=None,
            help='End date for data retrieval in YYYY-MM-DD format (default: today)'
        )

    def go(self, argv: list) -> int:
        """Main execution method."""
        # Parse arguments and set up logger (BaseApp infrastructure)
        super().go(argv)

        # Parse dates
        try:
            start_date_obj = date.fromisoformat(self.args.start_date)
        except ValueError:
            self.logger.error(f"Invalid start date format: {self.args.start_date} (expected YYYY-MM-DD)")
            return 1

        if self.args.end_date:
            try:
                end_date_obj = date.fromisoformat(self.args.end_date)
            except ValueError:
                self.logger.error(f"Invalid end date format: {self.args.end_date} (expected YYYY-MM-DD)")
                return 1
        else:
            end_date_obj = date.today()

        # Load credentials
        try:
            secrets_path = Path(self.args.secrets_file)
            if not secrets_path.exists():
                self.logger.error(f"Secrets file not found: {self.args.secrets_file}")
                self.logger.error("Please create a JSON file with 'userid' and 'password' fields.")
                return 1

            with open(secrets_path, 'r') as f:
                creds = json.load(f)

            if 'userid' not in creds or 'password' not in creds:
                self.logger.error("Secrets file must contain 'userid' and 'password' fields")
                return 1

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in secrets file: {e}")
            return 1
        except Exception as e:
            self.logger.error(f"Failed to read secrets file: {e}")
            return 1

        # Fetch data using the Water Meter API
        try:
            self.logger.info("Initializing water meter connection")
            meter = CpauWaterMeter(
                username=creds['userid'],
                password=creds['password'],
                headless=True
            )

            # Get usage data
            self.logger.info(f"Fetching {self.args.interval} data from {start_date_obj} to {end_date_obj}")
            usage_records = meter.get_usage(
                interval=self.args.interval,
                start_date=start_date_obj,
                end_date=end_date_obj
            )

            self.logger.info(f"Retrieved {len(usage_records)} records")

            # Determine fieldnames based on interval type
            # Note: For water meter, import_kwh contains gallons (not kWh)
            if self.args.interval == 'billing':
                fieldnames = ['date', 'billing_period_start', 'billing_period_end', 'billing_period_length', 'gallons']
            else:
                fieldnames = ['date', 'gallons']

            # Convert UsageRecord objects to dicts for CSV output
            rows = []
            for record in usage_records:
                row = {
                    'date': record.date.isoformat() if self.args.interval == 'hourly' else record.date.strftime('%Y-%m-%d'),
                    'gallons': record.import_kwh,  # import_kwh field contains gallons for water
                }
                if self.args.interval == 'billing':
                    row['billing_period_start'] = record.billing_period_start
                    row['billing_period_end'] = record.billing_period_end
                    row['billing_period_length'] = record.billing_period_length
                rows.append(row)

            # Write CSV output
            if self.args.output_file:
                try:
                    with open(self.args.output_file, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                        writer.writeheader()
                        writer.writerows(rows)
                    self.logger.info(f"Wrote {len(rows)} records to {self.args.output_file}")
                except Exception as e:
                    self.logger.error(f"Failed to write output file: {e}")
                    return 1
            else:
                # Write to stdout
                writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(rows)

            return 0

        except CpauError as e:
            self.logger.error(f"CPAU API error: {e}")
            return 1
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            if self.args.verbose:
                import traceback
                traceback.print_exc()
            return 1


def main_water():
    """Entry point for cpau-water command."""
    app = CpauWaterCli()
    return app.go(sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main_electric())
