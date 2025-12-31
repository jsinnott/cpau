"""Tests for CpauWaterMeter."""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, MagicMock, patch
import json

from cpau import CpauWaterMeter
from cpau.meter import UsageRecord

from tests.fixtures.water_responses import (
    HOURLY_USAGE_RESPONSE,
    DAILY_USAGE_RESPONSE,
    BILLING_USAGE_RESPONSE,
    MONTHLY_USAGE_RESPONSE,
    EMPTY_USAGE_RESPONSE,
    AVAILABILITY_RESPONSE,
)


@pytest.mark.unit
class TestCpauWaterMeter:
    """Tests for CpauWaterMeter water usage data retrieval."""

    @patch('cpau.water_meter.WaterSmartSession')
    def test_init_with_credentials(self, mock_watersmart_session, mock_credentials):
        """Test initializing water meter with credentials."""
        # Mock session
        mock_session = MagicMock()
        mock_session.get_cookies.return_value = {"session": "mock_cookie"}
        mock_watersmart_session.return_value = mock_session

        # Create water meter
        meter = CpauWaterMeter(
            username=mock_credentials['userid'],
            password=mock_credentials['password']
        )

        # Verify session was created
        mock_watersmart_session.assert_called_once()
        assert meter._session == mock_session

    @patch('cpau.water_meter.WaterSmartSession')
    def test_get_available_intervals(self, mock_watersmart_session, mock_credentials):
        """Test getting available intervals."""
        mock_session = MagicMock()
        mock_watersmart_session.return_value = mock_session

        meter = CpauWaterMeter(**mock_credentials)
        intervals = meter.get_available_intervals()

        assert 'billing' in intervals
        assert 'monthly' in intervals
        assert 'daily' in intervals
        assert 'hourly' in intervals
        assert '15min' not in intervals  # Water meter doesn't support 15min

    @patch('cpau.water_meter.WaterSmartSession')
    @patch('cpau.water_meter.requests.get')
    def test_get_daily_usage(self, mock_requests_get, mock_watersmart_session, mock_credentials):
        """Test retrieving daily water usage data."""
        # Mock session
        mock_session = MagicMock()
        mock_session.get_cookies.return_value = {"session": "mock_cookie"}
        mock_watersmart_session.return_value = mock_session

        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = DAILY_USAGE_RESPONSE
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response

        # Create meter and get usage
        meter = CpauWaterMeter(**mock_credentials)
        records = meter.get_daily_usage(
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 5)
        )

        # Verify results
        assert len(records) == 5
        assert records[0].date == datetime(2024, 12, 1)
        assert records[0].import_kwh == 168.309  # Gallons in import_kwh field
        assert records[0].export_kwh == 0.0
        assert records[0].net_kwh == 168.309

        assert records[1].date == datetime(2024, 12, 2)
        assert records[1].import_kwh == 222.169

    @patch('cpau.water_meter.WaterSmartSession')
    @patch('cpau.water_meter.requests.get')
    def test_get_hourly_usage(self, mock_requests_get, mock_watersmart_session, mock_credentials):
        """Test retrieving hourly water usage data."""
        mock_session = MagicMock()
        mock_session.get_cookies.return_value = {"session": "mock_cookie"}
        mock_watersmart_session.return_value = mock_session

        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = HOURLY_USAGE_RESPONSE
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response

        # Create meter and get usage
        meter = CpauWaterMeter(**mock_credentials)
        records = meter.get_hourly_usage(
            start_date=date(2023, 12, 17),
            end_date=date(2023, 12, 17)
        )

        # Verify results
        assert len(records) == 3
        assert records[0].import_kwh == 12.5
        assert records[1].import_kwh == 15.3
        assert records[2].import_kwh == 8.7

    @patch('cpau.water_meter.WaterSmartSession')
    @patch('cpau.water_meter.requests.get')
    def test_get_billing_usage(self, mock_requests_get, mock_watersmart_session, mock_credentials):
        """Test retrieving billing period water usage data."""
        mock_session = MagicMock()
        mock_session.get_cookies.return_value = {"session": "mock_cookie"}
        mock_watersmart_session.return_value = mock_session

        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = BILLING_USAGE_RESPONSE
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response

        # Create meter and get usage
        meter = CpauWaterMeter(**mock_credentials)
        records = meter.get_billing_usage(
            start_date=date(2024, 11, 1),
            end_date=date(2024, 12, 31)
        )

        # Verify results
        assert len(records) == 2
        assert records[0].import_kwh == 9724.0
        assert records[0].billing_period_start == datetime(2024, 11, 1)
        assert records[0].billing_period_end == datetime(2024, 11, 30, 23, 59, 59)
        assert records[0].billing_period_length == 30

        assert records[1].import_kwh == 10156.5
        assert records[1].billing_period_start == datetime(2024, 12, 1)

    @patch('cpau.water_meter.WaterSmartSession')
    @patch('cpau.water_meter.requests.get')
    def test_get_monthly_usage(self, mock_requests_get, mock_watersmart_session, mock_credentials):
        """Test retrieving monthly aggregated water usage."""
        mock_session = MagicMock()
        mock_session.get_cookies.return_value = {"session": "mock_cookie"}
        mock_watersmart_session.return_value = mock_session

        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = MONTHLY_USAGE_RESPONSE
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response

        # Create meter and get usage
        meter = CpauWaterMeter(**mock_credentials)
        records = meter.get_monthly_usage(
            start_date=date(2024, 11, 1),
            end_date=date(2024, 11, 30)
        )

        # Verify results - should have one record for November
        assert len(records) == 1
        assert records[0].date == datetime(2024, 11, 1)
        # Sum of all daily values: 150+160+...+255 = 5625.0
        assert records[0].import_kwh == 5625.0

    @patch('cpau.water_meter.WaterSmartSession')
    def test_invalid_interval(self, mock_watersmart_session, mock_credentials):
        """Test that invalid interval raises ValueError."""
        mock_session = MagicMock()
        mock_watersmart_session.return_value = mock_session

        meter = CpauWaterMeter(**mock_credentials)

        with pytest.raises(ValueError, match="Invalid interval"):
            meter.get_usage(
                interval='15min',  # Not supported for water
                start_date=date(2024, 12, 1),
                end_date=date(2024, 12, 31)
            )

    @patch('cpau.water_meter.WaterSmartSession')
    def test_invalid_date_range(self, mock_watersmart_session, mock_credentials):
        """Test that invalid date range raises ValueError."""
        mock_session = MagicMock()
        mock_watersmart_session.return_value = mock_session

        meter = CpauWaterMeter(**mock_credentials)

        with pytest.raises(ValueError, match="end_date.*must be >= start_date"):
            meter.get_usage(
                interval='daily',
                start_date=date(2024, 12, 31),
                end_date=date(2024, 12, 1)  # End before start
            )

    @patch('cpau.water_meter.WaterSmartSession')
    @patch('cpau.water_meter.requests.get')
    def test_empty_response(self, mock_requests_get, mock_watersmart_session, mock_credentials):
        """Test handling empty API response."""
        mock_session = MagicMock()
        mock_session.get_cookies.return_value = {"session": "mock_cookie"}
        mock_watersmart_session.return_value = mock_session

        # Mock empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = EMPTY_USAGE_RESPONSE
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response

        # Create meter and get usage
        meter = CpauWaterMeter(**mock_credentials)
        records = meter.get_hourly_usage(
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 31)
        )

        # Verify empty results
        assert len(records) == 0

    @patch('cpau.water_meter.WaterSmartSession')
    @patch('cpau.water_meter.requests.get')
    def test_get_availability_window(self, mock_requests_get, mock_watersmart_session, mock_credentials):
        """Test getting data availability window."""
        mock_session = MagicMock()
        mock_session.get_cookies.return_value = {"session": "mock_cookie"}
        mock_watersmart_session.return_value = mock_session

        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = AVAILABILITY_RESPONSE
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response

        # Create meter and get availability
        meter = CpauWaterMeter(**mock_credentials)
        earliest, latest = meter.get_availability_window('daily')

        # Verify results
        assert earliest == date(2017, 1, 1)
        assert latest == date(2024, 12, 31)

    @patch('cpau.water_meter.WaterSmartSession')
    def test_default_end_date(self, mock_watersmart_session, mock_credentials):
        """Test that end_date defaults to today for water meter."""
        mock_session = MagicMock()
        mock_watersmart_session.return_value = mock_session

        meter = CpauWaterMeter(**mock_credentials)

        # Patch the actual data fetch method to verify it's called
        with patch.object(meter, '_fetch_daily_data') as mock_fetch:
            mock_fetch.return_value = DAILY_USAGE_RESPONSE

            # Get usage without end_date
            meter.get_daily_usage(start_date=date(2024, 12, 1))

            # Verify method was called (end_date should default to today)
            assert mock_fetch.called

    @patch('cpau.water_meter.WaterSmartSession')
    @patch('cpau.water_meter.requests.get')
    def test_timeout_handling(self, mock_requests_get, mock_watersmart_session, mock_credentials):
        """Test handling of timeout errors."""
        mock_session = MagicMock()
        mock_watersmart_session.return_value = mock_session

        # Mock timeout error
        import requests
        mock_requests_get.side_effect = requests.exceptions.Timeout()

        meter = CpauWaterMeter(**mock_credentials)

        with pytest.raises(TimeoutError):
            meter.get_daily_usage(
                start_date=date(2024, 12, 1),
                end_date=date(2024, 12, 5)
            )

    @patch('cpau.water_meter.WaterSmartSession')
    @patch('cpau.water_meter.requests.get')
    def test_connection_error_handling(self, mock_requests_get, mock_watersmart_session, mock_credentials):
        """Test handling of connection errors."""
        mock_session = MagicMock()
        mock_watersmart_session.return_value = mock_session

        # Mock connection error
        import requests
        mock_requests_get.side_effect = requests.exceptions.ConnectionError()

        meter = CpauWaterMeter(**mock_credentials)

        with pytest.raises(ConnectionError):
            meter.get_daily_usage(
                start_date=date(2024, 12, 1),
                end_date=date(2024, 12, 5)
            )
