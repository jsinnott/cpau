"""
CPAU Electric Meter Implementation

This module provides the CpauElectricMeter class for retrieving electric
meter usage data from the CPAU portal.
"""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional, Iterator

from .meter import CpauMeter, UsageRecord
from .exceptions import CpauApiError

logger = logging.getLogger(__name__)


class CpauElectricMeter(CpauMeter):
    """
    Represents a CPAU electric meter and provides methods to retrieve usage data.

    Supports four interval types:
    - monthly: Billing period data (roughly monthly)
    - daily: Daily aggregated usage
    - hourly: Hourly usage data
    - 15min: 15-minute interval usage data
    """

    # Map interval names to API mode codes
    _INTERVAL_MODE_MAP = {
        'monthly': 'M',
        'daily': 'D',
        'hourly': 'H',
        '15min': 'MI'
    }

    def get_available_intervals(self) -> list[str]:
        """
        Get list of supported interval types for electric meters.

        Returns:
            ['monthly', 'daily', 'hourly', '15min']
        """
        return list(self._INTERVAL_MODE_MAP.keys())

    @property
    def rate_category(self) -> str:
        """Get the rate category/schedule for this meter."""
        return self._meter_info.get('MeterAttribute2', '')

    def get_usage(
        self,
        interval: str,
        start_date: date,
        end_date: Optional[date] = None
    ) -> list[UsageRecord]:
        """
        Retrieve usage data for the specified interval and date range.

        Args:
            interval: One of 'monthly', 'daily', 'hourly', '15min'
            start_date: Start date (inclusive)
            end_date: End date (inclusive). If None, defaults to 2 days ago.

        Returns:
            List of UsageRecord objects sorted by date

        Raises:
            ValueError: If interval is invalid or date range is invalid
            CpauApiError: If API request fails

        Notes:
            - For monthly interval, billing periods that overlap the date range are included
            - For other intervals, only data within the exact date range is returned
            - Date range is limited to data available from CPAU (typically not within last 2 days)
        """
        # Validate interval
        if interval not in self._INTERVAL_MODE_MAP:
            logger.error(f"Invalid interval: {interval}")
            raise ValueError(
                f"Invalid interval '{interval}'. Must be one of: {', '.join(self.get_available_intervals())}"
            )

        # Default end_date to 2 days ago
        if end_date is None:
            end_date = date.today() - timedelta(days=2)

        logger.info(f"Fetching {interval} usage data from {start_date} to {end_date}")

        # Validate date range
        if end_date < start_date:
            logger.error(f"Invalid date range: end_date ({end_date}) < start_date ({start_date})")
            raise ValueError(f"end_date ({end_date}) must be >= start_date ({start_date})")

        two_days_ago = date.today() - timedelta(days=2)
        if end_date > two_days_ago:
            logger.error(f"end_date ({end_date}) is too recent (must be <= {two_days_ago})")
            raise ValueError(f"end_date ({end_date}) cannot be later than 2 days ago ({two_days_ago})")

        # Get mode code
        mode = self._INTERVAL_MODE_MAP[interval]
        logger.debug(f"Using API mode: {mode}")

        # Fetch data based on interval type
        if mode == 'M':
            logger.debug("Fetching monthly billing data")
            raw_records = self._fetch_monthly_data()
        elif mode == 'D':
            logger.debug("Fetching daily data")
            raw_records = self._fetch_daily_data(start_date, end_date)
        else:  # Hourly or 15min
            logger.debug(f"Fetching {interval} data")
            raw_records = self._fetch_hourly_or_15min_data(mode, start_date, end_date)

        logger.debug(f"Retrieved {len(raw_records)} raw records from API")

        # Parse and filter records
        usage_records = self._parse_records(raw_records, interval, start_date, end_date)

        logger.info(f"Retrieved {len(usage_records)} {interval} usage records")
        return usage_records

    def get_monthly_usage(
        self,
        start_date: date,
        end_date: Optional[date] = None
    ) -> list[UsageRecord]:
        """
        Retrieve monthly billing period data.

        Convenience method equivalent to get_usage(interval='monthly', ...)

        Returns:
            List of UsageRecord objects with billing_period attribute populated
        """
        return self.get_usage('monthly', start_date, end_date)

    def get_daily_usage(
        self,
        start_date: date,
        end_date: Optional[date] = None
    ) -> list[UsageRecord]:
        """
        Retrieve daily usage data.

        Convenience method equivalent to get_usage(interval='daily', ...)
        """
        return self.get_usage('daily', start_date, end_date)

    def get_hourly_usage(
        self,
        start_date: date,
        end_date: Optional[date] = None
    ) -> list[UsageRecord]:
        """
        Retrieve hourly usage data.

        Convenience method equivalent to get_usage(interval='hourly', ...)

        Note: For large date ranges, this makes one API call per day and may be slow.
        """
        return self.get_usage('hourly', start_date, end_date)

    def get_15min_usage(
        self,
        start_date: date,
        end_date: Optional[date] = None
    ) -> list[UsageRecord]:
        """
        Retrieve 15-minute interval usage data.

        Convenience method equivalent to get_usage(interval='15min', ...)

        Note: For large date ranges, this makes one API call per day and may be slow.
        """
        return self.get_usage('15min', start_date, end_date)

    def iter_usage(
        self,
        interval: str,
        start_date: date,
        end_date: Optional[date] = None,
        chunk_days: int = 30
    ) -> Iterator[UsageRecord]:
        """
        Iterate over usage data in chunks to avoid loading large datasets into memory.

        Args:
            interval: One of 'monthly', 'daily', 'hourly', '15min'
            start_date: Start date (inclusive)
            end_date: End date (inclusive). If None, defaults to 2 days ago.
            chunk_days: Number of days to fetch per API request (default 30)

        Yields:
            UsageRecord objects one at a time

        Notes:
            - Useful for processing large date ranges without loading all data into memory
            - Not applicable to monthly interval (always returns all billing periods)
        """
        if end_date is None:
            end_date = date.today() - timedelta(days=2)

        if interval == 'monthly':
            # Monthly data returns everything at once, so just yield from get_usage
            for record in self.get_usage(interval, start_date, end_date):
                yield record
            return

        # For other intervals, process in chunks
        current_start = start_date
        while current_start <= end_date:
            current_end = min(current_start + timedelta(days=chunk_days - 1), end_date)
            chunk_records = self.get_usage(interval, current_start, current_end)
            for record in chunk_records:
                yield record
            current_start = current_end + timedelta(days=1)

    # Private methods for fetching data

    def _fetch_monthly_data(self) -> list[dict]:
        """Fetch all monthly billing period data."""
        payload = {
            'UsageOrGeneration': '1',
            'Type': 'K',
            'Mode': 'M',
            'strDate': '',
            'hourlyType': 'H',
            'SeasonId': '',
            'weatherOverlay': 0,
            'usageyear': '',
            'MeterNumber': self.meter_number,
            'DateFromDaily': '',
            'DateToDaily': '',
            'IsTier': True,
            'IsTou': False
        }

        data = self._session._make_api_request('LoadUsage', payload)
        return data.get('objUsageGenerationResultSetTwo', [])

    def _fetch_daily_data(self, start_date: date, end_date: date) -> list[dict]:
        """
        Fetch daily data for the specified date range.

        The API returns 30-day windows ending on strDate, so we may need
        multiple API calls for ranges > 30 days.
        """
        days_in_range = (end_date - start_date).days + 1
        all_records = []

        if days_in_range <= 30:
            logger.debug(f"Fetching daily data with single API call ({days_in_range} days)")
            # Single API call
            payload = {
                'UsageOrGeneration': '1',
                'Type': 'K',
                'Mode': 'D',
                'strDate': end_date.strftime('%m/%d/%y'),
                'hourlyType': 'H',
                'SeasonId': 0,
                'weatherOverlay': 0,
                'usageyear': '',
                'MeterNumber': self.meter_number,
                'DateFromDaily': '',
                'DateToDaily': '',
                'IsTier': True,
                'IsTou': False
            }

            data = self._session._make_api_request('LoadUsage', payload)
            all_records = data.get('objUsageGenerationResultSetTwo', [])
        else:
            # Multiple API calls needed - fetch in 30-day chunks from end date backwards
            num_calls = (days_in_range + 29) // 30  # Ceiling division
            logger.debug(f"Fetching daily data with multiple API calls ({num_calls} calls for {days_in_range} days)")
            current_end = end_date
            seen_dates = set()  # Track dates to avoid duplicates
            call_count = 0

            while current_end >= start_date:
                call_count += 1
                logger.debug(f"Daily data API call {call_count}/{num_calls} for date {current_end}")
                payload = {
                    'UsageOrGeneration': '1',
                    'Type': 'K',
                    'Mode': 'D',
                    'strDate': current_end.strftime('%m/%d/%y'),
                    'hourlyType': 'H',
                    'SeasonId': 0,
                    'weatherOverlay': 0,
                    'usageyear': '',
                    'MeterNumber': self.meter_number,
                    'DateFromDaily': '',
                    'DateToDaily': '',
                    'IsTier': True,
                    'IsTou': False
                }

                data = self._session._make_api_request('LoadUsage', payload)
                records = data.get('objUsageGenerationResultSetTwo', [])

                # Add records, avoiding duplicates
                for record in records:
                    date_key = record.get('UsageDate')
                    if date_key and date_key not in seen_dates:
                        all_records.append(record)
                        seen_dates.add(date_key)

                # Move back 30 days for next iteration
                current_end = current_end - timedelta(days=30)

        return all_records

    def _fetch_hourly_or_15min_data(self, mode: str, start_date: date, end_date: date) -> list[dict]:
        """
        Fetch hourly or 15-minute data for the specified date range.

        The API only supports single day per request, so we make one request per day.
        """
        days_in_range = (end_date - start_date).days + 1
        logger.debug(f"Fetching hourly/15min data: {days_in_range} API calls (one per day)")
        all_records = []
        current_date = start_date
        call_count = 0

        while current_date <= end_date:
            call_count += 1
            logger.debug(f"Hourly/15min data API call {call_count}/{days_in_range} for date {current_date}")
            payload = {
                'UsageOrGeneration': '1',
                'Type': 'K',
                'Mode': mode,
                'strDate': current_date.strftime('%m/%d/%y'),
                'hourlyType': 'H',
                'SeasonId': 0,
                'weatherOverlay': 0,
                'usageyear': '',
                'MeterNumber': self.meter_number,
                'DateFromDaily': '',
                'DateToDaily': '',
                'IsTier': True,
                'IsTou': False
            }

            data = self._session._make_api_request('LoadUsage', payload)
            records = data.get('objUsageGenerationResultSetTwo', [])
            all_records.extend(records)

            current_date = current_date + timedelta(days=1)

        return all_records

    def _parse_records(
        self,
        raw_records: list[dict],
        interval: str,
        start_date: date,
        end_date: date
    ) -> list[UsageRecord]:
        """
        Parse raw API records into UsageRecord objects.

        Handles grouping of import/export records and filtering by date range.
        """
        grouped_data = {}
        is_monthly = (interval == 'monthly')

        for record in raw_records:
            if is_monthly:
                # Monthly data: filter to billing periods that overlap with requested date range
                bill_period = record.get('BillPeriod', '')

                # Parse billing period dates (format: "MM/DD/YY to MM/DD/YY")
                if ' to ' in bill_period:
                    try:
                        period_start_str, period_end_str = bill_period.split(' to ')
                        period_start_dt = datetime.strptime(period_start_str.strip(), '%m/%d/%y')
                        period_end_dt = datetime.strptime(period_end_str.strip(), '%m/%d/%y')

                        # Check if billing period overlaps with requested date range
                        period_start_date = period_start_dt.date()
                        period_end_date = period_end_dt.date()

                        if period_end_date < start_date or period_start_date > end_date:
                            continue  # Skip billing periods outside the requested range
                    except ValueError:
                        # If we can't parse the billing period, include it to be safe
                        pass

                # Monthly data: group by Year-Month
                key = f"{record['Year']}-{record['Month']:02d}"
                if key not in grouped_data:
                    # Use the start date of the billing period as the datetime
                    if ' to ' in bill_period:
                        period_start_str = bill_period.split(' to ')[0].strip()
                        try:
                            period_datetime = datetime.strptime(period_start_str, '%m/%d/%y')
                        except ValueError:
                            period_datetime = datetime(record['Year'], record['Month'], 1)
                    else:
                        period_datetime = datetime(record['Year'], record['Month'], 1)

                    grouped_data[key] = {
                        'date': period_datetime,
                        'billing_period': bill_period,
                        'export_kwh': 0.0,
                        'import_kwh': 0.0,
                    }
            else:
                # Daily/Hourly/15min data: group by UsageDate (and time for hourly/15min)

                # Parse the usage date from API format (MM/DD/YY)
                record_dt = datetime.strptime(record['UsageDate'], '%m/%d/%y')
                record_date = record_dt.date()

                # For daily mode, filter to requested date range
                if interval == 'daily':
                    if record_date < start_date or record_date > end_date:
                        continue  # Skip records outside the requested range

                # Convert to datetime for output
                if interval in ['hourly', '15min'] and record.get('Hourly'):
                    # Hourly/15min: combine date and time
                    time_str = record['Hourly']  # Format: "HH:MM"
                    key = f"{record['UsageDate']} {time_str}"
                    try:
                        record_datetime = datetime.strptime(
                            f"{record_dt.strftime('%Y-%m-%d')} {time_str}:00",
                            '%Y-%m-%d %H:%M:%S'
                        )
                    except ValueError:
                        record_datetime = record_dt
                else:
                    # Daily: just the date
                    key = record['UsageDate']
                    record_datetime = record_dt

                if key not in grouped_data:
                    grouped_data[key] = {
                        'date': record_datetime,
                        'export_kwh': 0.0,
                        'import_kwh': 0.0,
                    }

            # Accumulate usage values
            usage_type = record.get('UsageType', '')
            usage_value = float(record.get('UsageValue', 0))

            if usage_type == 'Eusage':  # Export (generation)
                grouped_data[key]['export_kwh'] = abs(usage_value)
            elif usage_type == 'IUsage':  # Import (consumption)
                grouped_data[key]['import_kwh'] = usage_value

        # Convert to UsageRecord objects
        usage_records = []
        for key in sorted(grouped_data.keys()):
            period_data = grouped_data[key]
            net_kwh = period_data['import_kwh'] - period_data['export_kwh']

            record = UsageRecord(
                date=period_data['date'],
                import_kwh=period_data['import_kwh'],
                export_kwh=period_data['export_kwh'],
                net_kwh=net_kwh,
                billing_period=period_data.get('billing_period')
            )
            usage_records.append(record)

        return usage_records
