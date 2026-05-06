"""Tests for CpauWaterMeter."""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, MagicMock, patch
import requests

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


def _setup_session_manager(mock_manager_class, response_payload=None, side_effect=None):
    """Wire up a mocked WatersmartSessionManager class so that
    `manager.get_session().get(url, ...)` returns a configurable response.

    Returns the (manager_instance_mock, session_mock) for further customization.
    """
    mock_manager = MagicMock()
    mock_manager_class.return_value = mock_manager

    mock_session = MagicMock()
    mock_manager.get_session.return_value = mock_session

    if response_payload is not None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_payload
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response

    if side_effect is not None:
        mock_session.get.side_effect = side_effect

    return mock_manager, mock_session


@pytest.mark.unit
class TestCpauWaterMeter:
    """Tests for CpauWaterMeter water usage data retrieval."""

    @patch('cpau.water_meter.WatersmartSessionManager')
    def test_init_with_credentials(self, mock_manager_class, mock_credentials):
        """Test initializing water meter with credentials."""
        mock_manager, _ = _setup_session_manager(mock_manager_class)

        meter = CpauWaterMeter(
            username=mock_credentials['userid'],
            password=mock_credentials['password']
        )

        # Verify the manager was constructed and stored on the meter.
        mock_manager_class.assert_called_once()
        assert meter._session_manager is mock_manager

    @patch('cpau.water_meter.WatersmartSessionManager')
    def test_get_available_intervals(self, mock_manager_class, mock_credentials):
        """Test getting available intervals."""
        _setup_session_manager(mock_manager_class)

        meter = CpauWaterMeter(
            username=mock_credentials['userid'],
            password=mock_credentials['password']
        )
        intervals = meter.get_available_intervals()

        assert 'billing' in intervals
        assert 'monthly' in intervals
        assert 'daily' in intervals
        assert 'hourly' in intervals
        assert '15min' not in intervals  # Water meter doesn't support 15min

    @patch('cpau.water_meter.WatersmartSessionManager')
    def test_get_daily_usage(self, mock_manager_class, mock_credentials):
        """Test retrieving daily water usage data."""
        _setup_session_manager(mock_manager_class, response_payload=DAILY_USAGE_RESPONSE)

        meter = CpauWaterMeter(
            username=mock_credentials['userid'],
            password=mock_credentials['password']
        )
        records = meter.get_daily_usage(
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 5)
        )

        assert len(records) == 5
        assert records[0].date == datetime(2024, 12, 1)
        assert records[0].import_kwh == 168.309  # Gallons in import_kwh field
        assert records[0].export_kwh == 0.0
        assert records[0].net_kwh == 168.309

        assert records[1].date == datetime(2024, 12, 2)
        assert records[1].import_kwh == 222.169

    @patch('cpau.water_meter.WatersmartSessionManager')
    def test_get_hourly_usage(self, mock_manager_class, mock_credentials):
        """Test retrieving hourly water usage data."""
        _setup_session_manager(mock_manager_class, response_payload=HOURLY_USAGE_RESPONSE)

        meter = CpauWaterMeter(
            username=mock_credentials['userid'],
            password=mock_credentials['password']
        )
        records = meter.get_hourly_usage(
            start_date=date(2023, 12, 17),
            end_date=date(2023, 12, 17)
        )

        assert len(records) == 3
        assert records[0].import_kwh == 12.5
        assert records[1].import_kwh == 15.3
        assert records[2].import_kwh == 8.7

    @patch('cpau.water_meter.WatersmartSessionManager')
    def test_get_billing_usage(self, mock_manager_class, mock_credentials):
        """Test retrieving billing period water usage data."""
        _setup_session_manager(mock_manager_class, response_payload=BILLING_USAGE_RESPONSE)

        meter = CpauWaterMeter(
            username=mock_credentials['userid'],
            password=mock_credentials['password']
        )
        records = meter.get_billing_usage(
            start_date=date(2024, 11, 1),
            end_date=date(2024, 12, 31)
        )

        assert len(records) == 2
        assert records[0].import_kwh == 9724.0
        # billing_period_start/end are ISO date strings (per UsageRecord
        # dataclass), not datetimes; the parser reformats the API's
        # full-precision datetime into 'YYYY-MM-DD'.
        assert records[0].billing_period_start == '2024-11-01'
        assert records[0].billing_period_end == '2024-11-30'
        assert records[0].billing_period_length == 30

        assert records[1].import_kwh == 10156.5
        assert records[1].billing_period_start == '2024-12-01'

    @patch('cpau.water_meter.WatersmartSessionManager')
    def test_get_monthly_usage(self, mock_manager_class, mock_credentials):
        """Test retrieving monthly aggregated water usage."""
        _setup_session_manager(mock_manager_class, response_payload=MONTHLY_USAGE_RESPONSE)

        meter = CpauWaterMeter(
            username=mock_credentials['userid'],
            password=mock_credentials['password']
        )
        records = meter.get_monthly_usage(
            start_date=date(2024, 11, 1),
            end_date=date(2024, 11, 30)
        )

        # Monthly aggregates daily data into one record per calendar month.
        assert len(records) == 1
        assert records[0].date == datetime(2024, 11, 1)
        # Sum of all 30 daily fixture values for November 2024.
        assert records[0].import_kwh == 5755.0

    @patch('cpau.water_meter.WatersmartSessionManager')
    def test_invalid_interval(self, mock_manager_class, mock_credentials):
        """Test that invalid interval raises ValueError."""
        _setup_session_manager(mock_manager_class)

        meter = CpauWaterMeter(
            username=mock_credentials['userid'],
            password=mock_credentials['password']
        )

        with pytest.raises(ValueError, match="Invalid interval"):
            meter.get_usage(
                interval='15min',  # Not supported for water
                start_date=date(2024, 12, 1),
                end_date=date(2024, 12, 31)
            )

    @patch('cpau.water_meter.WatersmartSessionManager')
    def test_invalid_date_range(self, mock_manager_class, mock_credentials):
        """Test that invalid date range raises ValueError."""
        _setup_session_manager(mock_manager_class)

        meter = CpauWaterMeter(
            username=mock_credentials['userid'],
            password=mock_credentials['password']
        )

        with pytest.raises(ValueError, match="end_date.*must be >= start_date"):
            meter.get_usage(
                interval='daily',
                start_date=date(2024, 12, 31),
                end_date=date(2024, 12, 1)  # End before start
            )

    @patch('cpau.water_meter.WatersmartSessionManager')
    def test_empty_response(self, mock_manager_class, mock_credentials):
        """Test handling empty API response."""
        _setup_session_manager(mock_manager_class, response_payload=EMPTY_USAGE_RESPONSE)

        meter = CpauWaterMeter(
            username=mock_credentials['userid'],
            password=mock_credentials['password']
        )
        records = meter.get_hourly_usage(
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 31)
        )

        assert len(records) == 0

    @patch('cpau.water_meter.WatersmartSessionManager')
    def test_get_availability_window(self, mock_manager_class, mock_credentials):
        """Test getting data availability window."""
        _setup_session_manager(mock_manager_class, response_payload=AVAILABILITY_RESPONSE)

        meter = CpauWaterMeter(
            username=mock_credentials['userid'],
            password=mock_credentials['password']
        )
        earliest, latest = meter.get_availability_window('daily')

        assert earliest == date(2017, 1, 1)
        assert latest == date(2024, 12, 31)

    @patch('cpau.water_meter.WatersmartSessionManager')
    def test_default_end_date(self, mock_manager_class, mock_credentials):
        """Test that end_date defaults to today for water meter."""
        _setup_session_manager(mock_manager_class)

        meter = CpauWaterMeter(
            username=mock_credentials['userid'],
            password=mock_credentials['password']
        )

        with patch.object(meter, '_fetch_daily_data') as mock_fetch:
            mock_fetch.return_value = DAILY_USAGE_RESPONSE
            meter.get_daily_usage(start_date=date(2024, 12, 1))
            assert mock_fetch.called

    @patch('cpau.water_meter.WatersmartSessionManager')
    def test_timeout_handling(self, mock_manager_class, mock_credentials):
        """Test handling of timeout errors."""
        _setup_session_manager(
            mock_manager_class,
            side_effect=requests.exceptions.Timeout(),
        )

        meter = CpauWaterMeter(
            username=mock_credentials['userid'],
            password=mock_credentials['password']
        )

        with pytest.raises(TimeoutError):
            meter.get_daily_usage(
                start_date=date(2024, 12, 1),
                end_date=date(2024, 12, 5)
            )

    @patch('cpau.water_meter.WatersmartSessionManager')
    def test_connection_error_handling(self, mock_manager_class, mock_credentials):
        """Test handling of connection errors."""
        _setup_session_manager(
            mock_manager_class,
            side_effect=requests.exceptions.ConnectionError(),
        )

        meter = CpauWaterMeter(
            username=mock_credentials['userid'],
            password=mock_credentials['password']
        )

        with pytest.raises(ConnectionError):
            meter.get_daily_usage(
                start_date=date(2024, 12, 1),
                end_date=date(2024, 12, 5)
            )
