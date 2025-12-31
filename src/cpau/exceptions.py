"""
CPAU API Exception Classes

This module defines custom exceptions for the CPAU API library.
"""


class CpauError(Exception):
    """Base exception for all CPAU API errors."""
    pass


class CpauConnectionError(CpauError):
    """Raised when unable to connect to CPAU portal."""
    pass


class CpauAuthenticationError(CpauError):
    """Raised when authentication fails."""
    pass


class CpauApiError(CpauError):
    """Raised when API request fails."""
    pass


class CpauMeterNotFoundError(CpauError):
    """Raised when specified meter is not found."""
    pass
