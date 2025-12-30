"""
CPAU Meter Base Classes

This module defines the abstract base class for all meter types and the
UsageRecord dataclass for representing usage data.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .session import CpauApiSession


@dataclass
class UsageRecord:
    """
    Represents a single usage data point.

    Attributes:
        date: Date (or datetime for hourly/15min) of the reading
        import_kwh: Energy imported from grid (consumption)
        export_kwh: Energy exported to grid (solar generation)
        net_kwh: Net energy (import - export)
        billing_period: Optional billing period string (monthly data only)
    """
    date: datetime
    import_kwh: float
    export_kwh: float
    net_kwh: float
    billing_period: Optional[str] = None


class CpauMeter(ABC):
    """
    Abstract base class for CPAU meters.

    This class defines the common interface for all meter types and should
    not be instantiated directly. Use CpauElectricMeter or future meter
    subclasses instead.
    """

    def __init__(self, session: 'CpauApiSession', meter_info: dict):
        """
        Initialize a meter object.

        Args:
            session: Authenticated CpauApiSession
            meter_info: Dictionary containing meter details from API

        Note: This should only be called by CpauApiSession factory methods,
              not directly by library consumers.
        """
        self._session = session
        self._meter_info = meter_info

    @property
    def meter_number(self) -> str:
        """Get the meter number/identifier."""
        return self._meter_info.get('MeterNumber', '')

    @property
    def meter_type(self) -> str:
        """Get the meter type ('E' for electric, 'W' for water)."""
        return self._meter_info.get('MeterType', '')

    @property
    def address(self) -> str:
        """Get the service address for this meter."""
        return self._meter_info.get('Address', '')

    @property
    def status(self) -> int:
        """Get the meter status (1 = active)."""
        return self._meter_info.get('Status', 0)

    @abstractmethod
    def get_available_intervals(self) -> list[str]:
        """
        Get list of supported interval types for this meter.

        Returns:
            List of interval type strings (e.g., ['monthly', 'daily', 'hourly', '15min'])
        """
        pass

    def __repr__(self) -> str:
        """String representation of the meter."""
        return f"{self.__class__.__name__}(meter_number='{self.meter_number}', address='{self.address}')"
