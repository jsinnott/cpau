"""Tests for CpauApiSession and CpauElectricMeter."""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, MagicMock, patch, PropertyMock
import json

from cpau import CpauApiSession, CpauElectricMeter
from cpau.exceptions import CpauAuthenticationError, CpauApiError
from cpau.meter import UsageRecord

from tests.fixtures.electric_responses import (
    LOGIN_PAGE_HTML,
    LOGIN_SUCCESS_RESPONSE,
    METER_INFO_RESPONSE,
    DAILY_USAGE_RESPONSE,
    HOURLY_USAGE_RESPONSE,
    FIFTEEN_MIN_USAGE_RESPONSE,
    BILLING_USAGE_RESPONSE,
    EMPTY_USAGE_RESPONSE,
)


@pytest.mark.unit
class TestCpauApiSession:
    """Tests for CpauApiSession authentication and session management."""

    @patch('cpau.session.requests.Session')
    def test_login_success(self, mock_session_class, mock_credentials):
        """Test successful login."""
        # Setup mock responses
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Mock login page response
        login_page_response = Mock()
        login_page_response.status_code = 200
        login_page_response.text = LOGIN_PAGE_HTML

        # Mock login POST response
        login_post_response = Mock()
        login_post_response.status_code = 200
        login_post_response.json.return_value = LOGIN_SUCCESS_RESPONSE

        mock_session.get.return_value = login_page_response
        mock_session.post.return_value = login_post_response

        # Create session
        session = CpauApiSession(**mock_credentials)

        # Verify login was called
        assert mock_session.get.called
        assert mock_session.post.called
        assert session.is_authenticated

    @patch('cpau.session.requests.Session')
    def test_login_failure(self, mock_session_class):
        """Test failed login with invalid credentials."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Mock login page
        login_page_response = Mock()
        login_page_response.status_code = 200
        login_page_response.text = LOGIN_PAGE_HTML

        # Mock failed login response
        login_post_response = Mock()
        login_post_response.status_code = 401

        mock_session.get.return_value = login_page_response
        mock_session.post.return_value = login_post_response

        # Attempt to create session should raise error
        with pytest.raises(CpauAuthenticationError):
            CpauApiSession(userid='bad@example.com', password='wrong')

    @patch('cpau.session.requests.Session')
    def test_get_electric_meter(self, mock_session_class, mock_credentials):
        """Test retrieving electric meter."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Mock login
        login_page_response = Mock()
        login_page_response.status_code = 200
        login_page_response.text = LOGIN_PAGE_HTML

        login_post_response = Mock()
        login_post_response.status_code = 200
        login_post_response.json.return_value = LOGIN_SUCCESS_RESPONSE

        # Mock meter info response
        meter_response = Mock()
        meter_response.status_code = 200
        meter_response.json.return_value = METER_INFO_RESPONSE

        mock_session.get.return_value = login_page_response
        mock_session.post.side_effect = [login_post_response, meter_response]

        # Get meter
        session = CpauApiSession(**mock_credentials)
        meter = session.get_electric_meter()

        assert isinstance(meter, CpauElectricMeter)
        assert meter.meter_number == "12345678"
        assert meter.meter_type == "E"

    @patch('cpau.session.requests.Session')
    def test_context_manager(self, mock_session_class, mock_credentials):
        """Test using session as context manager."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Mock login
        login_page_response = Mock()
        login_page_response.status_code = 200
        login_page_response.text = LOGIN_PAGE_HTML

        login_post_response = Mock()
        login_post_response.status_code = 200
        login_post_response.json.return_value = LOGIN_SUCCESS_RESPONSE

        mock_session.get.return_value = login_page_response
        mock_session.post.return_value = login_post_response

        # Use as context manager
        with CpauApiSession(**mock_credentials) as session:
            assert session.is_authenticated

        # Verify session was closed
        mock_session.close.assert_called_once()


@pytest.mark.unit
class TestCpauElectricMeter:
    """Tests for CpauElectricMeter usage data retrieval."""

    def create_mock_meter(self):
        """Create a mock CpauElectricMeter with mocked session."""
        mock_session = MagicMock()
        mock_session._make_api_request = MagicMock()

        meter_info = json.loads(METER_INFO_RESPONSE['d'])['MeterDetails'][0]
        meter = CpauElectricMeter(mock_session, meter_info)

        return meter, mock_session

    def test_get_available_intervals(self):
        """Test getting available intervals."""
        meter, _ = self.create_mock_meter()

        intervals = meter.get_available_intervals()

        assert 'billing' in intervals
        assert 'monthly' in intervals
        assert 'daily' in intervals
        assert 'hourly' in intervals
        assert '15min' in intervals

    def test_meter_properties(self):
        """Test meter property accessors."""
        meter, _ = self.create_mock_meter()

        assert meter.meter_number == "12345678"
        assert meter.meter_type == "E"
        assert meter.address == "123 Test St, Palo Alto, CA"
        assert meter.status == 1
        assert meter.rate_category == "E-1 Residential"

    def test_get_daily_usage(self):
        """Test retrieving daily usage data."""
        meter, mock_session = self.create_mock_meter()

        # Mock API response
        response_data = json.loads(DAILY_USAGE_RESPONSE['d'])
        mock_session._make_api_request.return_value = response_data

        # Get usage
        records = meter.get_daily_usage(
            start_date=date(2024, 12, 15),
            end_date=date(2024, 12, 16)
        )

        # Verify results
        assert len(records) == 2
        assert records[0].date == datetime(2024, 12, 15)
        assert records[0].import_kwh == 28.06
        assert records[0].export_kwh == 0.10
        assert records[1].date == datetime(2024, 12, 16)
        assert records[1].import_kwh == 22.25
        assert records[1].export_kwh == 1.43

    def test_get_hourly_usage(self):
        """Test retrieving hourly usage data."""
        meter, mock_session = self.create_mock_meter()

        # Mock API response
        response_data = json.loads(HOURLY_USAGE_RESPONSE['d'])
        mock_session._make_api_request.return_value = response_data

        # Get usage
        records = meter.get_hourly_usage(
            start_date=date(2024, 12, 17),
            end_date=date(2024, 12, 17)
        )

        # Verify results
        assert len(records) == 2
        assert records[0].date == datetime(2024, 12, 17, 0, 0)
        assert records[0].import_kwh == 0.58
        assert records[1].date == datetime(2024, 12, 17, 1, 0)
        assert records[1].import_kwh == 0.64

    def test_get_15min_usage(self):
        """Test retrieving 15-minute usage data."""
        meter, mock_session = self.create_mock_meter()

        # Mock API response
        response_data = json.loads(FIFTEEN_MIN_USAGE_RESPONSE['d'])
        mock_session._make_api_request.return_value = response_data

        # Get usage
        records = meter.get_15min_usage(
            start_date=date(2024, 12, 17),
            end_date=date(2024, 12, 17)
        )

        # Verify results
        assert len(records) == 2
        assert records[0].date == datetime(2024, 12, 17, 0, 0)
        assert records[0].import_kwh == 0.15
        assert records[1].date == datetime(2024, 12, 17, 0, 15)
        assert records[1].import_kwh == 0.14

    def test_get_billing_usage(self):
        """Test retrieving billing period data."""
        meter, mock_session = self.create_mock_meter()

        # Mock API response
        response_data = json.loads(BILLING_USAGE_RESPONSE['d'])
        mock_session._make_api_request.return_value = response_data

        # Get usage
        records = meter.get_billing_usage(
            start_date=date(2024, 11, 1),
            end_date=date(2024, 12, 31)
        )

        # Verify results
        assert len(records) == 2
        assert records[0].import_kwh == 689.4
        assert records[0].export_kwh == 156.2
        assert records[1].import_kwh == 712.5
        assert records[1].export_kwh == 168.3

    def test_invalid_interval(self):
        """Test that invalid interval raises ValueError."""
        meter, _ = self.create_mock_meter()

        with pytest.raises(ValueError, match="Invalid interval"):
            meter.get_usage(
                interval='invalid',
                start_date=date(2024, 12, 1),
                end_date=date(2024, 12, 31)
            )

    def test_invalid_date_range(self):
        """Test that invalid date range raises ValueError."""
        meter, _ = self.create_mock_meter()

        with pytest.raises(ValueError, match="end_date.*must be >= start_date"):
            meter.get_usage(
                interval='daily',
                start_date=date(2024, 12, 31),
                end_date=date(2024, 12, 1)  # End before start
            )

    def test_empty_response(self):
        """Test handling empty API response."""
        meter, mock_session = self.create_mock_meter()

        # Mock empty response
        response_data = json.loads(EMPTY_USAGE_RESPONSE['d'])
        mock_session._make_api_request.return_value = response_data

        # Get usage
        records = meter.get_daily_usage(
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 31)
        )

        # Verify empty results
        assert len(records) == 0

    def test_default_end_date(self):
        """Test that end_date defaults to 2 days ago."""
        meter, mock_session = self.create_mock_meter()

        # Mock API response
        response_data = json.loads(DAILY_USAGE_RESPONSE['d'])
        mock_session._make_api_request.return_value = response_data

        # Get usage without end_date
        records = meter.get_daily_usage(start_date=date(2024, 12, 1))

        # Verify API was called (end_date should default)
        assert mock_session._make_api_request.called
