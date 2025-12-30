#!/usr/bin/env python3
"""
CPAU Meter Data Downloader
Downloads electric meter data from City of Palo Alto Utilities and outputs to stdout in CSV format
"""

import json
import sys
import re
import csv
import requests
from datetime import datetime, timedelta
from argparse import ArgumentParser
from typing import Optional

from baseapp import BaseApp


class CpauDownloader(BaseApp):

    def add_arg_definitions(self, parser: ArgumentParser) -> None:
        super().add_arg_definitions(parser)

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
            help='Path to JSON file containing CPAU login credentials (default: secrets.json), secrets keys are "userid" and "password"'
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

    def validate_and_convert_dates(self) -> tuple:
        """
        Validate and convert dates from YYYY-MM-DD to MM/DD/YY format
        Returns tuple of (start_date_api_format, end_date_api_format) or (None, None) on error
        """
        # Calculate default end date (2 days ago)
        two_days_ago = datetime.now() - timedelta(days=2)

        # Parse start date
        try:
            start_dt = datetime.strptime(self.args.start_date, '%Y-%m-%d')
        except ValueError:
            self.logger.error(f"invalid start date format: {self.args.start_date} (expected YYYY-MM-DD)")
            return None, None

        # Parse or default end date
        if self.args.end_date:
            try:
                end_dt = datetime.strptime(self.args.end_date, '%Y-%m-%d')
            except ValueError:
                self.logger.error(f"invalid end date format: {self.args.end_date} (expected YYYY-MM-DD)")
                return None, None
        else:
            end_dt = two_days_ago

        # Validate end >= start
        if end_dt < start_dt:
            self.logger.error(f"end date ({end_dt.strftime('%Y-%m-%d')}) must be >= start date ({start_dt.strftime('%Y-%m-%d')})")
            return None, None

        # Validate end is no later than 2 days ago
        if end_dt > two_days_ago:
            self.logger.error(f"end date ({end_dt.strftime('%Y-%m-%d')}) cannot be later than 2 days ago ({two_days_ago.strftime('%Y-%m-%d')})")
            return None, None

        # Convert to API format (MM/DD/YY)
        start_api = start_dt.strftime('%m/%d/%y')
        end_api = end_dt.strftime('%m/%d/%y')

        self.logger.debug(f"converted dates: {self.args.start_date} -> {start_api}, {end_dt.strftime('%Y-%m-%d')} -> {end_api}")

        return start_api, end_api

    def load_credentials(self) -> dict:
        """Load credentials from secrets file"""
        try:
            with open(self.args.secrets_file, 'r') as f:
                creds = json.load(f)

            # Validate required fields
            if 'userid' not in creds or 'password' not in creds:
                self.logger.error(f"secrets file must contain 'userid' and 'password' fields")
                return None

            return creds
        except FileNotFoundError:
            self.logger.error(f"secrets file not found: {self.args.secrets_file}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"invalid JSON in secrets file: {e}")
            return None

    def login(self, session: requests.Session, userid: str, password: str) -> bool:
        """
        Login to CPAU portal
        Returns True on success, False on failure
        """
        login_url = 'https://mycpau.cityofpaloalto.org/Portal/Default.aspx/validateLogin'

        # First, get the homepage to establish session cookies and extract CSRF token
        self.logger.debug("fetching homepage to establish session")
        homepage_response = session.get('https://mycpau.cityofpaloalto.org/Portal')

        # Extract CSRF token from the page
        csrf_token = None
        csrf_match = re.search(r'name="__RequestVerificationToken".*?value="([^"]+)"', homepage_response.text)
        if csrf_match:
            csrf_token = csrf_match.group(1)
            self.logger.debug(f"extracted CSRF token from homepage")

        # Prepare login payload with correct field names
        payload = {
            'username': userid,
            'password': password,
            'rememberme': False,
            'calledFrom': 'LN',
            'ExternalLoginId': '',
            'LoginMode': '1'
        }

        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'isajax': '1',
            'Referer': 'https://mycpau.cityofpaloalto.org/Portal/'
        }

        # Add CSRF token if found
        if csrf_token:
            headers['csrftoken'] = csrf_token

        self.logger.debug("submitting login request")
        response = session.post(login_url, json=payload, headers=headers)

        if response.status_code == 200:
            try:
                data = response.json()
                # Check if login was successful
                if 'd' in data:
                    result = json.loads(data['d'])
                    # Result can be a dict or list
                    if isinstance(result, dict):
                        if result.get('STATUS') == '1' or 'UserID' in result:
                            self.logger.debug("login successful")
                            return True
                    elif isinstance(result, list) and len(result) > 0:
                        # Check first item in list
                        if result[0].get('STATUS') == '1' or 'UserID' in result[0]:
                            self.logger.debug("login successful")
                            return True
            except Exception as e:
                self.logger.error(f"login response error: {e}")
                self.logger.debug(f"response: {response.text[:500]}")

        self.logger.error("login failed")
        return False

    def get_meter_data(self, session: requests.Session, date_from: str, date_to: str) -> Optional[dict]:
        """
        Fetch meter usage data
        Args:
            session: requests Session object
            date_from: Start date in MM/DD/YY format for API
            date_to: End date in MM/DD/YY format for API
        Returns parsed usage data or None on failure
        """
        # First, navigate to the Usages page to establish session state
        self.logger.info("loading Usages page")
        usages_page = session.get('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx')
        if usages_page.status_code != 200:
            self.logger.error(f"failed to load Usages page (status {usages_page.status_code})")
            return None

        # Extract CSRF token from the Usages page (it's in a hidden field)
        csrf_token = None
        csrf_match = re.search(r'name="ctl00\$hdnCSRFToken".*?value="([^"]+)"', usages_page.text)
        if csrf_match:
            csrf_token = csrf_match.group(1)
            self.logger.debug("extracted CSRF token from Usages page")
        else:
            self.logger.error("CSRF token not found in page")
            return None

        # Now make the API calls
        usage_url = 'https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/LoadUsage'
        meter_url = 'https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/BindMultiMeter'

        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://mycpau.cityofpaloalto.org/Portal/Usages.aspx'
        }

        # Add CSRF token
        if csrf_token:
            headers['csrftoken'] = csrf_token

        # Get meter info with correct payload
        self.logger.debug("fetching meter information")
        meter_response = session.post(meter_url, json={'MeterType': 'E'}, headers=headers)

        if meter_response.status_code != 200:
            self.logger.error(f"failed to fetch meter information (status {meter_response.status_code})")
            return None

        try:
            meter_data = meter_response.json()
            meter_info = json.loads(meter_data['d'])

            # Get the active meter
            active_meter = None
            if 'MeterDetails' in meter_info:
                for meter in meter_info['MeterDetails']:
                    if meter['Status'] == 1:  # Active meter
                        active_meter = meter
                        break

            if not active_meter:
                self.logger.error("no active meter found")
                return None

            self.logger.info(f"found active meter: {active_meter['MeterNumber']}")

            # Map interval argument to API mode
            interval_map = {
                'monthly': 'M',
                'daily': 'D',
                'hourly': 'H',
                '15min': 'MI'
            }
            mode = interval_map[self.args.interval]

            # SeasonId is 0 for non-monthly modes when using dates
            season_id = '' if mode == 'M' else 0

            self.logger.debug(f"requesting data: interval={self.args.interval} (mode={mode}), from={date_from}, to={date_to}")

            # Fetch usage data
            # The API behaves differently for each mode:
            # - Daily (D): strDate is end date, returns 30 days ending on that date
            # - Hourly/15min (H/MI): strDate specifies a single day only
            # - DateFromDaily/DateToDaily are ignored by the API

            all_records = []

            if mode == 'M':
                # Monthly mode: single API call with empty dates (returns all billing periods)
                usage_payload = {
                    'UsageOrGeneration': '1',
                    'Type': 'K',
                    'Mode': mode,
                    'strDate': '',
                    'hourlyType': 'H',
                    'SeasonId': season_id,
                    'weatherOverlay': 0,
                    'usageyear': '',
                    'MeterNumber': active_meter['MeterNumber'],
                    'DateFromDaily': '',
                    'DateToDaily': '',
                    'IsTier': True,
                    'IsTou': False
                }

                self.logger.debug("fetching monthly billing data")
                usage_response = session.post(usage_url, json=usage_payload, headers=headers)

                if usage_response.status_code == 200:
                    usage_data = usage_response.json()
                    parsed_data = json.loads(usage_data['d'])
                    all_records = parsed_data.get('objUsageGenerationResultSetTwo', [])
                else:
                    self.logger.error(f"failed to fetch usage data (status {usage_response.status_code})")
                    return None

            elif mode == 'D':
                # Daily mode: API returns 30 days ending on strDate
                # For ranges > 30 days, make multiple API calls
                start_dt = datetime.strptime(date_from, '%m/%d/%y')
                end_dt = datetime.strptime(date_to, '%m/%d/%y')
                days_in_range = (end_dt - start_dt).days + 1

                if days_in_range <= 30:
                    # Single API call
                    usage_payload = {
                        'UsageOrGeneration': '1',
                        'Type': 'K',
                        'Mode': mode,
                        'strDate': date_to,  # API returns 30 days ending on this date
                        'hourlyType': 'H',
                        'SeasonId': season_id,
                        'weatherOverlay': 0,
                        'usageyear': '',
                        'MeterNumber': active_meter['MeterNumber'],
                        'DateFromDaily': '',
                        'DateToDaily': '',
                        'IsTier': True,
                        'IsTou': False
                    }

                    self.logger.debug(f"fetching daily data ending on {date_to}")
                    usage_response = session.post(usage_url, json=usage_payload, headers=headers)

                    if usage_response.status_code == 200:
                        usage_data = usage_response.json()
                        parsed_data = json.loads(usage_data['d'])
                        all_records = parsed_data.get('objUsageGenerationResultSetTwo', [])
                    else:
                        self.logger.error(f"failed to fetch usage data (status {usage_response.status_code})")
                        return None
                else:
                    # Multiple API calls needed - fetch in 30-day chunks from end date backwards
                    current_end = end_dt
                    seen_dates = set()  # Track dates to avoid duplicates

                    while current_end >= start_dt:
                        current_end_str = current_end.strftime('%m/%d/%y')

                        usage_payload = {
                            'UsageOrGeneration': '1',
                            'Type': 'K',
                            'Mode': mode,
                            'strDate': current_end_str,
                            'hourlyType': 'H',
                            'SeasonId': season_id,
                            'weatherOverlay': 0,
                            'usageyear': '',
                            'MeterNumber': active_meter['MeterNumber'],
                            'DateFromDaily': '',
                            'DateToDaily': '',
                            'IsTier': True,
                            'IsTou': False
                        }

                        self.logger.debug(f"fetching daily data ending on {current_end_str}")
                        usage_response = session.post(usage_url, json=usage_payload, headers=headers)

                        if usage_response.status_code == 200:
                            usage_data = usage_response.json()
                            parsed_data = json.loads(usage_data['d'])
                            records = parsed_data.get('objUsageGenerationResultSetTwo', [])

                            # Add records, avoiding duplicates
                            for record in records:
                                date_key = record.get('UsageDate')
                                if date_key and date_key not in seen_dates:
                                    all_records.append(record)
                                    seen_dates.add(date_key)
                        else:
                            self.logger.error(f"failed to fetch usage data for {current_end_str} (status {usage_response.status_code})")
                            return None

                        # Move back 30 days for next iteration
                        current_end -= timedelta(days=30)

            else:
                # Hourly/15min modes: API only supports single day per request
                # Make one request per day in the range
                start_dt = datetime.strptime(date_from, '%m/%d/%y')
                end_dt = datetime.strptime(date_to, '%m/%d/%y')

                current_dt = start_dt
                while current_dt <= end_dt:
                    current_date_str = current_dt.strftime('%m/%d/%y')

                    usage_payload = {
                        'UsageOrGeneration': '1',
                        'Type': 'K',
                        'Mode': mode,
                        'strDate': current_date_str,  # Single day
                        'hourlyType': 'H',
                        'SeasonId': season_id,
                        'weatherOverlay': 0,
                        'usageyear': '',
                        'MeterNumber': active_meter['MeterNumber'],
                        'DateFromDaily': '',
                        'DateToDaily': '',
                        'IsTier': True,
                        'IsTou': False
                    }

                    self.logger.debug(f"fetching {self.args.interval} data for {current_date_str}")
                    usage_response = session.post(usage_url, json=usage_payload, headers=headers)

                    if usage_response.status_code == 200:
                        usage_data = usage_response.json()
                        parsed_data = json.loads(usage_data['d'])
                        records = parsed_data.get('objUsageGenerationResultSetTwo', [])
                        all_records.extend(records)
                    else:
                        self.logger.error(f"failed to fetch usage data for {current_date_str} (status {usage_response.status_code})")
                        return None

                    current_dt += timedelta(days=1)

            self.logger.info("successfully retrieved usage data")
            return {
                'meter_info': active_meter,
                'usage_data': {'objUsageGenerationResultSetTwo': all_records}
            }

        except Exception as e:
            self.logger.error(f"error parsing meter data: {e}")
            return None

    def format_output(self, data: dict) -> Optional[dict]:
        """Format the data for output"""
        if not data:
            return None

        meter_info = data['meter_info']
        usage_data = data['usage_data']

        output = {
            'meter': {
                'number': meter_info['MeterNumber'],
                'type': meter_info['MeterType'],
                'address': meter_info['Address'],
                'rate_category': meter_info.get('MeterAttribute2', '')
            },
            'usage_summary': [],
            'retrieved_at': datetime.now().isoformat()
        }

        # Parse usage records
        if 'objUsageGenerationResultSetTwo' in usage_data:
            usage_records = usage_data['objUsageGenerationResultSetTwo']

            grouped_data = {}

            # Determine if this is monthly or date-based data
            is_monthly = self.args.interval == 'monthly'

            # Parse user's requested date range for filtering
            start_dt = datetime.strptime(self.args.start_date, '%Y-%m-%d')
            if self.args.end_date:
                end_dt = datetime.strptime(self.args.end_date, '%Y-%m-%d')
            else:
                end_dt = datetime.now() - timedelta(days=2)

            for record in usage_records:
                if is_monthly:
                    # Monthly data: filter to billing periods that overlap with requested date range
                    bill_period = record.get('BillPeriod', '')

                    # Parse billing period dates (format: "MM/DD/YY to MM/DD/YY")
                    if ' to ' in bill_period:
                        try:
                            period_start_str, period_end_str = bill_period.split(' to ')
                            period_start = datetime.strptime(period_start_str.strip(), '%m/%d/%y')
                            period_end = datetime.strptime(period_end_str.strip(), '%m/%d/%y')

                            # Check if billing period overlaps with requested date range
                            # Overlap occurs if: period_end >= start_dt AND period_start <= end_dt
                            if period_end < start_dt or period_start > end_dt:
                                continue  # Skip billing periods outside the requested range
                        except ValueError:
                            # If we can't parse the billing period, include it to be safe
                            pass

                    # Monthly data: group by Year-Month
                    key = f"{record['Year']}-{record['Month']:02d}"
                    if key not in grouped_data:
                        grouped_data[key] = {
                            'date': key,
                            'billing_period': bill_period,
                            'export_kwh': 0.0,
                            'import_kwh': 0.0,
                            'net_kwh': 0.0
                        }
                else:
                    # Daily/Hourly/15min data: group by UsageDate (and time for hourly/15min)

                    # Parse the usage date from API format (MM/DD/YY)
                    record_dt = datetime.strptime(record['UsageDate'], '%m/%d/%y')

                    # For daily mode, filter to requested date range
                    if self.args.interval == 'daily':
                        if record_dt < start_dt or record_dt > end_dt:
                            continue  # Skip records outside the requested range

                    # Convert to ISO format for output
                    if self.args.interval in ['hourly', '15min'] and record.get('Hourly'):
                        # Hourly/15min: YYYY-MM-DD HH:MM:SS format
                        key = f"{record['UsageDate']} {record['Hourly']}"
                        # Parse time and combine with date
                        time_str = record['Hourly']  # Format: "HH:MM"
                        date_str = f"{record_dt.strftime('%Y-%m-%d')} {time_str}:00"
                    else:
                        # Daily: YYYY-MM-DD format
                        key = record['UsageDate']
                        date_str = record_dt.strftime('%Y-%m-%d')

                    if key not in grouped_data:
                        grouped_data[key] = {
                            'date': date_str,
                            'export_kwh': 0.0,
                            'import_kwh': 0.0,
                            'net_kwh': 0.0
                        }

                usage_type = record.get('UsageType', '')
                usage_value = float(record.get('UsageValue', 0))

                if usage_type == 'Eusage':  # Export (generation)
                    grouped_data[key]['export_kwh'] = abs(usage_value)
                elif usage_type == 'IUsage':  # Import (consumption)
                    grouped_data[key]['import_kwh'] = usage_value

            # Calculate net and prepare output
            for key in sorted(grouped_data.keys()):
                period_data = grouped_data[key]
                period_data['net_kwh'] = period_data['import_kwh'] - period_data['export_kwh']
                output['usage_summary'].append(period_data)

        interval_label = self.args.interval if hasattr(self, 'args') else 'records'
        self.logger.info(f"formatted {len(output['usage_summary'])} {interval_label} records")
        return output

    def go(self, argv: list) -> int:
        super().go(argv)

        # Load credentials
        creds = self.load_credentials()
        if not creds:
            return 1

        # Create session
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

        # Validate and convert dates
        date_from, date_to = self.validate_and_convert_dates()
        if date_from is None or date_to is None:
            return 1

        # Login
        self.logger.info("logging in to CPAU portal")
        if not self.login(session, creds['userid'], creds['password']):
            return 1

        # Fetch meter data
        self.logger.info("fetching meter data")
        data = self.get_meter_data(session, date_from, date_to)

        if not data:
            return 1

        # Format output
        output = self.format_output(data)
        if not output:
            return 1

        # Write CSV output
        # Determine fieldnames based on interval type
        if self.args.interval == 'monthly':
            fieldnames = ['date', 'billing_period', 'export_kwh', 'import_kwh', 'net_kwh']
        else:
            fieldnames = ['date', 'export_kwh', 'import_kwh', 'net_kwh']

        if self.args.output_file:
            try:
                with open(self.args.output_file, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    writer.writerows(output['usage_summary'])
                self.logger.info(f"wrote output to {self.args.output_file}")
            except Exception as e:
                self.logger.error(f"failed to write output file: {e}")
                return 1
        else:
            # Write to stdout
            writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(output['usage_summary'])

        return 0


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app = CpauDownloader()
    sys.exit(app.go(sys.argv[1:]))
