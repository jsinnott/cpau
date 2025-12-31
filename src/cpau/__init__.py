"""
CPAU API Library

A Python library for accessing City of Palo Alto Utilities (CPAU) meter data.

This library provides a clean, pythonic interface to the CPAU web portal's
internal APIs, enabling programmatic access to electric and water meter usage data.

Basic Usage:
    >>> from cpau_api import CpauApiSession
    >>> from datetime import date
    >>>
    >>> # Create session and login
    >>> with CpauApiSession(userid='myuser', password='mypass') as session:
    ...     # Get the electric meter
    ...     meter = session.get_electric_meter()
    ...
    ...     # Get daily usage for December 2024
    ...     data = meter.get_daily_usage(
    ...         start_date=date(2024, 12, 1),
    ...         end_date=date(2024, 12, 31)
    ...     )
    ...
    ...     # Print results
    ...     for record in data:
    ...         print(f"{record.date}: {record.net_kwh} kWh")

Water Meter Usage:
    >>> from cpau import CpauWaterMeter
    >>> from datetime import date
    >>>
    >>> # Create water meter directly (uses SAML/SSO authentication)
    >>> meter = CpauWaterMeter(username='myuser', password='mypass')
    >>>
    >>> # Get daily water usage
    >>> data = meter.get_daily_usage(
    ...     start_date=date(2024, 12, 1),
    ...     end_date=date(2024, 12, 31)
    ... )
    >>>
    >>> # Print results (import_kwh contains gallons for water)
    >>> for record in data:
    ...     print(f"{record.date}: {record.import_kwh} gallons")

Classes:
    CpauApiSession: Main entry point for API access
    CpauElectricMeter: Electric meter interface
    CpauWaterMeter: Water meter interface
    UsageRecord: Data class representing a usage record

Exceptions:
    CpauError: Base exception for all CPAU API errors
    CpauConnectionError: Connection errors
    CpauAuthenticationError: Authentication failures
    CpauApiError: API request errors
    CpauMeterNotFoundError: Meter not found errors
"""

from .session import CpauApiSession
from .electric_meter import CpauElectricMeter
from .water_meter import CpauWaterMeter
from .meter import UsageRecord
from .exceptions import (
    CpauError,
    CpauConnectionError,
    CpauAuthenticationError,
    CpauApiError,
    CpauMeterNotFoundError
)

__version__ = '0.1.0'

__all__ = [
    'CpauApiSession',
    'CpauElectricMeter',
    'CpauWaterMeter',
    'UsageRecord',
    'CpauError',
    'CpauConnectionError',
    'CpauAuthenticationError',
    'CpauApiError',
    'CpauMeterNotFoundError',
]
