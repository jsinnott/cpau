"""Shared pytest fixtures for CPAU tests."""

import pytest
from datetime import date
from unittest.mock import Mock, MagicMock


@pytest.fixture
def mock_credentials():
    """Provide mock credentials for testing."""
    return {
        "userid": "test@example.com",
        "password": "test_password"
    }


@pytest.fixture
def sample_date_range():
    """Provide a sample date range for testing."""
    return {
        "start_date": date(2024, 12, 1),
        "end_date": date(2024, 12, 31)
    }


@pytest.fixture
def mock_meter_info():
    """Provide mock meter information."""
    return {
        "MeterNumber": "12345678",
        "MeterType": "E",
        "MeterAddress": "123 Test St, Palo Alto, CA",
        "MeterStatus": 1,
        "MeterAttribute2": "E-1 Residential"
    }


@pytest.fixture
def mock_requests_session():
    """Create a mock requests.Session object."""
    session = MagicMock()
    session.cookies = {}
    session.headers = {}
    return session


@pytest.fixture
def mock_playwright_page():
    """Create a mock Playwright page object."""
    page = MagicMock()
    page.goto = MagicMock()
    page.fill = MagicMock()
    page.click = MagicMock()
    page.wait_for_url = MagicMock()
    page.context = MagicMock()
    page.context.cookies = MagicMock(return_value=[
        {
            "name": "watersmart_session",
            "value": "mock_session_value",
            "domain": ".watersmart.com"
        }
    ])
    return page
