#!/usr/bin/env python3
"""
CPAU Water Meter Implementation

This module provides the CpauWaterMeter class for retrieving water
meter usage data from paloalto.watersmart.com.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from cpau.meter import UsageRecord
from cpau.watersmart_session import WatersmartSessionManager

logger = logging.getLogger(__name__)


class CpauWaterMeter:
    """
    Represents a CPAU water meter and provides methods to retrieve usage data.

    Supports four interval types:
    - billing: Billing period data (CPAU's billing periods, roughly monthly)
    - monthly: Calendar month aggregation (sum of daily data by month)
    - daily: Daily aggregated usage
    - hourly: Hourly usage data

    Note: Water meter data comes from paloalto.watersmart.com and requires
    browser automation (Playwright) for SAML/SSO authentication.

    Example:
        >>> meter = CpauWaterMeter(username='user', password='pass')
        >>> usage = meter.get_usage('daily', start_date, end_date)
        >>> for record in usage:
        ...     print(f"{record.date}: {record.import_kwh} gallons")
    """

    # Map interval names to watersmart API endpoints
    _INTERVAL_API_MAP = {
        'hourly': 'RealTimeChart',
        'daily': 'weatherConsumptionChart',
        'billing': 'BillingHistoryChart',
        'monthly': None,  # Aggregated from daily data
    }

    # Base URL for watersmart APIs
    _API_BASE_URL = 'https://paloalto.watersmart.com/index.php/rest/v1/Chart/'

    def __init__(self, username: str, password: str, headless: bool = True):
        """
        Initialize water meter with CPAU credentials.

        Args:
            username: CPAU username
            password: CPAU password
            headless: Run browser in headless mode (default: True)

        Note:
            First API call will trigger Playwright authentication (~15 seconds).
            Subsequent calls reuse the session cookies (<1 second each).
        """
        self.username = username
        self.password = password
        self._session_manager = WatersmartSessionManager(username, password, headless)

        logger.debug(f"Initialized CpauWaterMeter for user {username}")

    def get_available_intervals(self) -> list[str]:
        """
        Get list of supported interval types for water meters.

        Returns:
            ['billing', 'monthly', 'daily', 'hourly']
        """
        return list(self._INTERVAL_API_MAP.keys())

    def get_usage(
        self,
        interval: str,
        start_date: date,
        end_date: Optional[date] = None
    ) -> list[UsageRecord]:
        """
        Retrieve water usage data for the specified interval and date range.

        Args:
            interval: One of 'billing', 'monthly', 'daily', 'hourly'
            start_date: Start date (inclusive)
            end_date: End date (inclusive). If None, defaults to today.

        Returns:
            List of UsageRecord objects sorted by date

        Raises:
            ValueError: If interval is invalid or date range is invalid

        Notes:
            - First call authenticates via Playwright (~15s)
            - Subsequent calls reuse session (~1s each)
            - import_kwh field contains gallons (not kWh)
            - export_kwh is always 0 for water
            - net_kwh equals import_kwh
        """
        # Validate interval
        if interval not in self._INTERVAL_API_MAP:
            logger.error(f"Invalid interval: {interval}")
            raise ValueError(
                f"Invalid interval '{interval}'. Must be one of: {', '.join(self.get_available_intervals())}"
            )

        # Default end_date to today
        if end_date is None:
            end_date = date.today()

        logger.info(f"Fetching {interval} water usage from {start_date} to {end_date}")

        # Validate date range
        if end_date < start_date:
            logger.error(f"Invalid date range: end_date ({end_date}) < start_date ({start_date})")
            raise ValueError(f"end_date ({end_date}) must be >= start_date ({start_date})")

        # Get API endpoint
        api_name = self._INTERVAL_API_MAP[interval]

        # Special handling for monthly (calendar month aggregation)
        if interval == 'monthly':
            logger.debug("Aggregating daily data into calendar months")
            return self._aggregate_monthly(start_date, end_date)

        logger.debug(f"Using API: {api_name}")

        # Fetch data based on interval type
        if api_name == 'RealTimeChart':
            logger.debug("Fetching hourly data")
            raw_data = self._fetch_hourly_data()
        elif api_name == 'weatherConsumptionChart':
            logger.debug("Fetching daily data")
            raw_data = self._fetch_daily_data()
        elif api_name == 'BillingHistoryChart':
            logger.debug("Fetching billing period data")
            raw_data = self._fetch_billing_data()
        else:
            raise ValueError(f"Unknown API: {api_name}")

        logger.debug(f"Retrieved raw data from {api_name}")

        # Parse and filter records
        usage_records = self._parse_records(raw_data, interval, start_date, end_date)

        logger.info(f"Retrieved {len(usage_records)} {interval} usage records")
        return usage_records

    def _fetch_hourly_data(self) -> dict:
        """Fetch hourly data from RealTimeChart API."""
        import requests

        try:
            session = self._session_manager.get_session()
            url = f"{self._API_BASE_URL}RealTimeChart"

            logger.debug(f"GET {url}")
            response = session.get(url, timeout=30)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.Timeout:
            logger.error("Timeout while fetching hourly data")
            raise TimeoutError("Request to RealTimeChart API timed out after 30 seconds")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error while fetching hourly data: {e}")
            raise ConnectionError(f"Failed to connect to watersmart.com: {e}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error while fetching hourly data: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid JSON response from RealTimeChart API: {e}")
            raise ValueError(f"API returned invalid JSON: {e}")

    def _fetch_daily_data(self) -> dict:
        """Fetch daily data from weatherConsumptionChart API."""
        import requests

        try:
            session = self._session_manager.get_session()
            url = f"{self._API_BASE_URL}weatherConsumptionChart?module=portal&commentary=full"

            logger.debug(f"GET {url}")
            response = session.get(url, timeout=30)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.Timeout:
            logger.error("Timeout while fetching daily data")
            raise TimeoutError("Request to weatherConsumptionChart API timed out after 30 seconds")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error while fetching daily data: {e}")
            raise ConnectionError(f"Failed to connect to watersmart.com: {e}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error while fetching daily data: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid JSON response from weatherConsumptionChart API: {e}")
            raise ValueError(f"API returned invalid JSON: {e}")

    def _fetch_billing_data(self) -> dict:
        """Fetch billing period data from BillingHistoryChart API."""
        import requests

        try:
            session = self._session_manager.get_session()
            url = f"{self._API_BASE_URL}BillingHistoryChart?flowType=per_day&comparison=cohort"

            logger.debug(f"GET {url}")
            response = session.get(url, timeout=30)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.Timeout:
            logger.error("Timeout while fetching billing data")
            raise TimeoutError("Request to BillingHistoryChart API timed out after 30 seconds")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error while fetching billing data: {e}")
            raise ConnectionError(f"Failed to connect to watersmart.com: {e}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error while fetching billing data: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid JSON response from BillingHistoryChart API: {e}")
            raise ValueError(f"API returned invalid JSON: {e}")

    def _parse_records(
        self,
        raw_data: dict,
        interval: str,
        start_date: date,
        end_date: date
    ) -> list[UsageRecord]:
        """
        Parse raw API response into UsageRecord objects.

        Args:
            raw_data: Raw JSON response from watersmart API
            interval: Interval type ('hourly', 'daily', 'billing')
            start_date: Filter start date
            end_date: Filter end date

        Returns:
            List of UsageRecord objects within date range
        """
        if interval == 'hourly':
            return self._parse_hourly_records(raw_data, start_date, end_date)
        elif interval == 'daily':
            return self._parse_daily_records(raw_data, start_date, end_date)
        elif interval == 'billing':
            return self._parse_billing_records(raw_data, start_date, end_date)
        else:
            raise ValueError(f"Unknown interval: {interval}")

    def _parse_hourly_records(
        self,
        raw_data: dict,
        start_date: date,
        end_date: date
    ) -> list[UsageRecord]:
        """
        Parse hourly data from RealTimeChart API.

        Format:
        {
          "data": {
            "series": [
              {
                "read_datetime": 1723334400,  # Unix timestamp
                "gallons": 0,
                "flags": null,
                "leak_gallons": 0
              },
              ...
            ]
          }
        }
        """
        records = []

        if 'data' not in raw_data or 'series' not in raw_data['data']:
            logger.warning("No hourly data found in API response")
            return records

        series = raw_data['data']['series']

        for item in series:
            # Parse timestamp
            timestamp = item.get('read_datetime')
            if timestamp is None:
                continue

            dt = datetime.fromtimestamp(timestamp)

            # Filter by date range
            if dt.date() < start_date or dt.date() > end_date:
                continue

            # Get consumption
            gallons = float(item.get('gallons', 0))

            # Create record (water doesn't have import/export, so export=0, net=import)
            record = UsageRecord(
                date=dt,
                import_kwh=gallons,  # Actually gallons
                export_kwh=0.0,
                net_kwh=gallons,
                billing_period_start=None,
                billing_period_end=None,
                billing_period_length=None
            )

            records.append(record)

        return sorted(records, key=lambda r: r.date)

    def _parse_daily_records(
        self,
        raw_data: dict,
        start_date: date,
        end_date: date
    ) -> list[UsageRecord]:
        """
        Parse daily data from weatherConsumptionChart API.

        Format:
        {
          "data": {
            "chartData": {
              "dailyData": {
                "categories": ["2024-08-11", "2024-08-12", ...],
                "consumption": [10.472, 109.215, ...],
                "temperature": [60.25, 60.125, ...],
                "precipitation": [0, 0, ...]
              }
            }
          }
        }

        Data is in parallel arrays where consumption[i] corresponds to categories[i].
        """
        records = []

        if 'data' not in raw_data:
            logger.warning("No data found in API response")
            return records

        chart_data = raw_data['data'].get('chartData', {})
        daily_data = chart_data.get('dailyData', {})

        if not daily_data:
            logger.warning("No daily data found in API response")
            return records

        # Get parallel arrays
        categories = daily_data.get('categories', [])
        consumption = daily_data.get('consumption', [])

        if not categories or not consumption:
            logger.warning("Missing categories or consumption data")
            return records

        if len(categories) != len(consumption):
            logger.warning(f"Data mismatch: {len(categories)} dates but {len(consumption)} values")
            # Use the shorter length to avoid index errors
            length = min(len(categories), len(consumption))
        else:
            length = len(categories)

        # Parse each day
        for i in range(length):
            date_str = categories[i]
            gallons_val = consumption[i]

            # Parse date (format: "YYYY-MM-DD")
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                logger.warning(f"Could not parse date: {date_str}")
                continue

            # Filter by date range
            if dt.date() < start_date or dt.date() > end_date:
                continue

            # Handle null/None values
            if gallons_val is None:
                gallons = 0.0
            else:
                gallons = float(gallons_val)

            # Create record
            record = UsageRecord(
                date=dt,
                import_kwh=gallons,
                export_kwh=0.0,
                net_kwh=gallons,
                billing_period_start=None,
                billing_period_end=None,
                billing_period_length=None
            )

            records.append(record)

        return sorted(records, key=lambda r: r.date)

    def _parse_billing_records(
        self,
        raw_data: dict,
        start_date: date,
        end_date: date
    ) -> list[UsageRecord]:
        """
        Parse billing data from BillingHistoryChart API.

        Format:
        {
          "data": {
            "chart_data": [
              {
                "gallons": "9724.00",
                "period": {
                  "startDate": {"date": "2017-01-01 ..."},
                  "endDate": {"date": "2017-01-31 ..."},
                  ...
                }
              },
              ...
            ]
          }
        }
        """
        records = []

        if 'data' not in raw_data or 'chart_data' not in raw_data['data']:
            logger.warning("No billing data found in API response")
            return records

        chart_data = raw_data['data']['chart_data']

        for item in chart_data:
            # Get billing period info
            period = item.get('period', {})

            start_date_obj = period.get('startDate', {})
            end_date_obj = period.get('endDate', {})

            # Parse dates
            start_str = start_date_obj.get('date', '')
            end_str = end_date_obj.get('date', '')

            if not start_str or not end_str:
                continue

            # Parse datetime strings (format: "2017-01-01 00:00:00.000000")
            period_start = datetime.strptime(start_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
            period_end = datetime.strptime(end_str.split('.')[0], '%Y-%m-%d %H:%M:%S')

            # Filter by date range (check if period overlaps with requested range)
            if period_end.date() < start_date or period_start.date() > end_date:
                continue

            # Get consumption
            gallons = float(item.get('gallons', 0))

            # Calculate period length
            period_length = (period_end.date() - period_start.date()).days + 1

            # Create record
            record = UsageRecord(
                date=period_start,  # Use period start as the date
                import_kwh=gallons,
                export_kwh=0.0,
                net_kwh=gallons,
                billing_period_start=period_start.strftime('%Y-%m-%d'),
                billing_period_end=period_end.strftime('%Y-%m-%d'),
                billing_period_length=period_length
            )

            records.append(record)

        return sorted(records, key=lambda r: r.date)

    def _aggregate_monthly(self, start_date: date, end_date: date) -> list[UsageRecord]:
        """
        Aggregate daily data into calendar months.

        Expands the date range to include full calendar months, then groups
        daily consumption data by calendar month.

        For example, if start_date is 2024-08-15 and end_date is 2024-10-15,
        this will fetch data from 2024-08-01 to 2024-10-31 and return
        three monthly records (Aug, Sep, Oct).

        Args:
            start_date: Start date for aggregation
            end_date: End date for aggregation

        Returns:
            List of UsageRecord objects, one per calendar month
        """
        import calendar

        # Expand the date range to full calendar months
        # Start from the first day of the start month
        expanded_start = start_date.replace(day=1)

        # End on the last day of the end month
        _, last_day = calendar.monthrange(end_date.year, end_date.month)
        expanded_end = end_date.replace(day=last_day)

        logger.debug(f"Expanding date range for monthly aggregation: {start_date} to {end_date} -> {expanded_start} to {expanded_end}")

        # Fetch daily data for the expanded range
        logger.debug(f"Fetching daily data to aggregate into months: {expanded_start} to {expanded_end}")
        daily_records = self.get_usage('daily', expanded_start, expanded_end)

        if not daily_records:
            logger.warning(f"No daily data available for range {expanded_start} to {expanded_end}")
            return []

        # Group by calendar month
        monthly_data = {}
        for record in daily_records:
            # Extract year-month key
            record_date = record.date
            if isinstance(record_date, datetime):
                month_key = record_date.strftime('%Y-%m')
            else:
                month_key = record_date.strftime('%Y-%m')

            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'gallons': 0.0,
                }

            # Sum gallons for this month
            monthly_data[month_key]['gallons'] += record.import_kwh  # import_kwh contains gallons

        # Convert to UsageRecord objects
        usage_records = []
        for month_key in sorted(monthly_data.keys()):
            month_data = monthly_data[month_key]

            # Create datetime for first day of the month
            year, month = month_key.split('-')
            month_date = datetime(int(year), int(month), 1)

            gallons = month_data['gallons']

            record = UsageRecord(
                date=month_date,
                import_kwh=gallons,  # Still using import_kwh field for gallons
                export_kwh=0.0,       # Water doesn't export
                net_kwh=gallons,      # Same as import for water
                billing_period_start=None,
                billing_period_end=None,
                billing_period_length=None
            )
            usage_records.append(record)

        logger.info(f"Aggregated daily data into {len(usage_records)} calendar months")
        return usage_records

    # Convenience methods (matching electric meter API)
    def get_billing_usage(
        self,
        start_date: date,
        end_date: Optional[date] = None
    ) -> list[UsageRecord]:
        """Convenience method for billing period data."""
        return self.get_usage('billing', start_date, end_date)

    def get_monthly_usage(
        self,
        start_date: date,
        end_date: Optional[date] = None
    ) -> list[UsageRecord]:
        """Convenience method for monthly aggregated data."""
        return self.get_usage('monthly', start_date, end_date)

    def get_daily_usage(
        self,
        start_date: date,
        end_date: Optional[date] = None
    ) -> list[UsageRecord]:
        """Convenience method for daily data."""
        return self.get_usage('daily', start_date, end_date)

    def get_hourly_usage(
        self,
        start_date: date,
        end_date: Optional[date] = None
    ) -> list[UsageRecord]:
        """Convenience method for hourly data."""
        return self.get_usage('hourly', start_date, end_date)

    def get_availability_window(self, interval: str) -> tuple[Optional[date], Optional[date]]:
        """
        Find the earliest and latest dates for which data is available.

        Args:
            interval: One of 'billing', 'monthly', 'daily', 'hourly'

        Returns:
            Tuple of (earliest_date, latest_date) or (None, None) if no data found

        Notes:
            - For water meter, all intervals make a single API call that returns all available data
            - For 'monthly': Returns the daily data availability window (since monthly aggregates daily)
            - Total execution time: typically 1-2 seconds (after initial authentication)

        Raises:
            ValueError: If interval is invalid
        """
        # Validate interval
        if interval not in self._INTERVAL_API_MAP:
            logger.error(f"Invalid interval: {interval}")
            raise ValueError(
                f"Invalid interval '{interval}'. Must be one of: {', '.join(self.get_available_intervals())}"
            )

        logger.info(f"Finding data availability window for {interval} interval")

        # Monthly aggregation uses daily data availability
        if interval == 'monthly':
            logger.debug("Monthly interval: using daily data availability window")
            return self.get_availability_window('daily')

        # Fetch all data and scan for min/max dates
        try:
            # Fetch raw data (returns all available data)
            if interval == 'hourly':
                raw_data = self._fetch_hourly_data()
            elif interval == 'daily':
                raw_data = self._fetch_daily_data()
            elif interval == 'billing':
                raw_data = self._fetch_billing_data()
            else:
                raise ValueError(f"Unknown interval: {interval}")

            # Parse all records without date filtering
            # Use a very wide date range to get all data
            far_past = date(2000, 1, 1)
            far_future = date(2100, 12, 31)

            records = self._parse_records(raw_data, interval, far_past, far_future)

            if not records:
                logger.info(f"No data found for {interval} interval")
                return (None, None)

            # Find min and max dates
            earliest_dt = min(r.date for r in records)
            latest_dt = max(r.date for r in records)

            # Convert datetime to date if needed
            if isinstance(earliest_dt, datetime):
                earliest_date = earliest_dt.date()
            else:
                earliest_date = earliest_dt

            if isinstance(latest_dt, datetime):
                latest_date = latest_dt.date()
            else:
                latest_date = latest_dt

            logger.info(f"Availability window for {interval}: {earliest_date} to {latest_date}")
            return (earliest_date, latest_date)

        except Exception as e:
            logger.error(f"Error finding availability window for {interval}: {e}")
            return (None, None)

    def __repr__(self) -> str:
        """String representation."""
        return f"CpauWaterMeter(username='{self.username}')"
