"""Command-line interface for CPAU API tools.

Provides three CLI entry points:

- ``cpau-electric`` — download electric meter usage data
- ``cpau-water`` — download water meter usage data
- ``cpau-availability`` — report which intervals have data and the date
  range available for each meter type

All three share the credential-loading and logging behavior from
:class:`cpau.app.CpauApp`.
"""

import csv
import sys
from argparse import ArgumentParser
from datetime import date, timedelta

from .app import CpauApp
from .exceptions import CpauError
from .session import CpauApiSession
from .water_meter import CpauWaterMeter


class CpauElectricCli(CpauApp):
    """Command-line application for downloading CPAU electric meter data."""

    def add_arg_definitions(self, parser: ArgumentParser) -> None:
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
        rc = super().go(argv)
        if rc != 0:
            return rc

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

        try:
            self.logger.info("Connecting to CPAU portal")
            with CpauApiSession(
                userid=self.credentials.userid,
                password=self.credentials.password,
            ) as session:
                self.logger.info("Retrieving meter information")
                meter = session.get_electric_meter()
                self.logger.debug(f"Found meter: {meter.meter_number}")

                self.logger.info(f"Fetching {self.args.interval} data from {start_date_obj} to {end_date_obj}")
                usage_records = meter.get_usage(
                    interval=self.args.interval,
                    start_date=start_date_obj,
                    end_date=end_date_obj
                )

                self.logger.info(f"Retrieved {len(usage_records)} records")

                if self.args.interval == 'billing':
                    fieldnames = ['date', 'billing_period_start', 'billing_period_end', 'billing_period_length', 'export_kwh', 'import_kwh', 'net_kwh']
                else:
                    fieldnames = ['date', 'export_kwh', 'import_kwh', 'net_kwh']

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


class CpauWaterCli(CpauApp):
    """Command-line application for downloading CPAU water meter data."""

    def add_arg_definitions(self, parser: ArgumentParser) -> None:
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
            '--cache-dir',
            type=str,
            default='~/.cpau',
            help='Directory for caching authentication cookies (default: ~/.cpau)'
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
        rc = super().go(argv)
        if rc != 0:
            return rc

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

        try:
            self.logger.info("Initializing water meter connection")
            meter = CpauWaterMeter(
                username=self.credentials.userid,
                password=self.credentials.password,
                headless=True,
                cache_dir=self.args.cache_dir
            )

            self.logger.info(f"Fetching {self.args.interval} data from {start_date_obj} to {end_date_obj}")
            usage_records = meter.get_usage(
                interval=self.args.interval,
                start_date=start_date_obj,
                end_date=end_date_obj
            )

            self.logger.info(f"Retrieved {len(usage_records)} records")

            # For water meter, import_kwh contains gallons (not kWh).
            if self.args.interval == 'billing':
                fieldnames = ['date', 'billing_period_start', 'billing_period_end', 'billing_period_length', 'gallons']
            else:
                fieldnames = ['date', 'gallons']

            rows = []
            for record in usage_records:
                row = {
                    'date': record.date.isoformat() if self.args.interval == 'hourly' else record.date.strftime('%Y-%m-%d'),
                    'gallons': record.import_kwh,
                }
                if self.args.interval == 'billing':
                    row['billing_period_start'] = record.billing_period_start
                    row['billing_period_end'] = record.billing_period_end
                    row['billing_period_length'] = record.billing_period_length
                rows.append(row)

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


class CpauAvailabilityCli(CpauApp):
    """Command-line application for checking CPAU data availability."""

    def add_arg_definitions(self, parser: ArgumentParser) -> None:
        super().add_arg_definitions(parser)

        parser.add_argument(
            '--cache-dir',
            type=str,
            default='~/.cpau',
            help='Directory for caching water meter authentication cookies (default: ~/.cpau)'
        )

        parser.add_argument(
            '-o',
            '--output-file',
            type=str,
            default=None,
            help='Path to output file (default: stdout)'
        )

    def go(self, argv: list) -> int:
        rc = super().go(argv)
        if rc != 0:
            return rc

        availability_records = []

        try:
            self.logger.info("Checking electric meter data availability")
            with CpauApiSession(
                userid=self.credentials.userid,
                password=self.credentials.password,
            ) as session:
                meter = session.get_electric_meter()
                self.logger.debug(f"Found electric meter: {meter.meter_number}")

                for interval in meter.get_available_intervals():
                    self.logger.info(f"Checking electric {interval} data availability")
                    try:
                        earliest, latest = meter.get_availability_window(interval)
                        if earliest and latest:
                            availability_records.append({
                                'data_type': 'electric',
                                'interval': interval,
                                'data_start': earliest.isoformat(),
                                'data_end': latest.isoformat()
                            })
                            self.logger.debug(f"Electric {interval}: {earliest} to {latest}")
                        else:
                            self.logger.warning(f"No electric {interval} data available")
                    except Exception as e:
                        self.logger.warning(f"Failed to check electric {interval} availability: {e}")

        except CpauError as e:
            self.logger.error(f"Electric meter error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error checking electric meter: {e}")
            if self.args.verbose:
                import traceback
                traceback.print_exc()

        try:
            self.logger.info("Checking water meter data availability")
            water_meter = CpauWaterMeter(
                username=self.credentials.userid,
                password=self.credentials.password,
                cache_dir=self.args.cache_dir
            )

            for interval in water_meter.get_available_intervals():
                self.logger.info(f"Checking water {interval} data availability")
                try:
                    earliest, latest = water_meter.get_availability_window(interval)
                    if earliest and latest:
                        availability_records.append({
                            'data_type': 'water',
                            'interval': interval,
                            'data_start': earliest.isoformat(),
                            'data_end': latest.isoformat()
                        })
                        self.logger.debug(f"Water {interval}: {earliest} to {latest}")
                    else:
                        self.logger.warning(f"No water {interval} data available")
                except Exception as e:
                    self.logger.warning(f"Failed to check water {interval} availability: {e}")

        except Exception as e:
            self.logger.error(f"Water meter error: {e}")
            if self.args.verbose:
                import traceback
                traceback.print_exc()
            if not availability_records:
                return 1

        if not availability_records:
            self.logger.error("No availability data found for any meter type")
            return 1

        self.logger.info(f"Found availability data for {len(availability_records)} interval(s)")

        fieldnames = ['data_type', 'interval', 'data_start', 'data_end']

        try:
            if self.args.output_file:
                with open(self.args.output_file, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(availability_records)
                self.logger.info(f"Wrote {len(availability_records)} records to {self.args.output_file}")
            else:
                writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(availability_records)

            return 0

        except Exception as e:
            self.logger.error(f"Failed to write output: {e}")
            return 1


def main_availability():
    """Entry point for cpau-availability command."""
    app = CpauAvailabilityCli()
    return app.go(sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main_electric())
