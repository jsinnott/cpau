# CPAU API Library Design Document

## Overview

This document describes the design of a Python library that abstracts the CPAU (City of Palo Alto Utilities) web API interactions for both electric and water meter data. The library separates API concerns from CLI concerns, making CPAU data accessible to other applications programmatically.

## Design Goals

1. **Separation of Concerns**: Decouple API logic from CLI application logic
2. **Reusability**: Enable other applications to access CPAU data programmatically
3. **Multi-Meter Support**: Provide unified interface for both electric and water meter data
4. **Clean Abstractions**: Hide implementation details while exposing intuitive interfaces
5. **Type Safety**: Use type hints throughout for better IDE support and runtime checking

## Architecture

The library consists of four main classes:

```
CpauApiSession
    └── manages authentication, session state, CSRF tokens (for electric meter)
    └── provides factory methods for electric meter objects

CpauMeter (abstract base class)
    └── defines common meter interface
    └── handles shared meter operations

CpauElectricMeter (concrete implementation)
    └── implements electric meter-specific data retrieval
    └── supports multiple interval types (billing, monthly, daily, hourly, 15-minute)

CpauWaterMeter (concrete implementation)
    └── implements water meter-specific data retrieval
    └── handles SAML/SSO authentication via Playwright
    └── supports multiple interval types (billing, monthly, daily, hourly)
    └── implements cookie caching for fast re-authentication
```

---

## Class: CpauApiSession

### Purpose
Encapsulates all interactions with the CPAU web portal, including authentication, session management, and CSRF token handling. Serves as the entry point for the API and provides factory methods to obtain meter objects.

### Responsibilities
- Login to CPAU portal with userid/password
- Maintain authenticated session state
- Manage CSRF tokens for API requests
- Discover and enumerate available meters
- Provide factory methods to instantiate meter objects

### Public Interface

```python
class CpauApiSession:
    """
    Represents an authenticated session with the CPAU web portal.

    This class handles login, session management, and provides access to
    meter objects for retrieving usage data.
    """

    def __init__(self, userid: str, password: str):
        """
        Initialize a CPAU API session.

        Args:
            userid: CPAU account username
            password: CPAU account password

        Raises:
            CpauAuthenticationError: If login fails
            CpauConnectionError: If unable to connect to CPAU portal
        """
        pass

    def login(self) -> bool:
        """
        Authenticate with the CPAU portal.

        This method is called automatically by __init__ but can be called
        again to re-authenticate if the session expires.

        Returns:
            True if login successful, False otherwise

        Raises:
            CpauAuthenticationError: If credentials are invalid
            CpauConnectionError: If unable to connect to CPAU portal
        """
        pass

    def get_electric_meters(self) -> list['CpauElectricMeter']:
        """
        Retrieve all active electric meters associated with this account.

        Returns:
            List of CpauElectricMeter objects (typically just one)

        Raises:
            CpauApiError: If API request fails
        """
        pass

    def get_electric_meter(self, meter_number: Optional[str] = None) -> 'CpauElectricMeter':
        """
        Get a specific electric meter, or the default/only meter if meter_number is None.

        Args:
            meter_number: Optional meter number to retrieve. If None, returns the
                         first active meter found.

        Returns:
            CpauElectricMeter object

        Raises:
            CpauMeterNotFoundError: If specified meter not found
            CpauApiError: If API request fails
        """
        pass

    @property
    def is_authenticated(self) -> bool:
        """Check if the session is currently authenticated."""
        pass

    @property
    def session(self) -> requests.Session:
        """
        Get the underlying requests.Session object.

        This is exposed for use by meter objects but should not typically
        be used directly by library consumers.
        """
        pass

    def close(self) -> None:
        """
        Close the session and clean up resources.

        This should be called when done with the session, or use the
        session as a context manager.
        """
        pass

    def __enter__(self) -> 'CpauApiSession':
        """Support for context manager (with statement)."""
        pass

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Clean up when exiting context manager."""
        pass
```

### Private Interface (internal use by meter classes)

```python
    def _get_csrf_token(self, page_name: str) -> str:
        """Get CSRF token for a specific page."""
        pass

    def _make_api_request(self, endpoint: str, payload: dict) -> dict:
        """Make an authenticated API request with CSRF token handling."""
        pass
```

---

## Class: CpauMeter (Abstract Base Class)

### Purpose
Defines the common interface and shared functionality for all meter types (electric, water, etc.). This abstraction enables polymorphic code that works with any meter type.

### Responsibilities
- Define common meter attributes (number, address, etc.)
- Provide abstract methods that subclasses must implement
- Share common validation and error handling logic

### Public Interface

```python
from abc import ABC, abstractmethod

class CpauMeter(ABC):
    """
    Abstract base class for CPAU meters.

    This class defines the common interface for all meter types and should
    not be instantiated directly. Use CpauElectricMeter or future meter
    subclasses instead.
    """

    def __init__(self, session: CpauApiSession, meter_info: dict):
        """
        Initialize a meter object.

        Args:
            session: Authenticated CpauApiSession
            meter_info: Dictionary containing meter details from API

        Note: This should only be called by CpauApiSession factory methods,
              not directly by library consumers.
        """
        pass

    @property
    def meter_number(self) -> str:
        """Get the meter number/identifier."""
        pass

    @property
    def meter_type(self) -> str:
        """Get the meter type ('E' for electric, 'W' for water)."""
        pass

    @property
    def address(self) -> str:
        """Get the service address for this meter."""
        pass

    @property
    def status(self) -> int:
        """Get the meter status (1 = active)."""
        pass

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
        pass
```

---

## Class: CpauElectricMeter

### Purpose
Concrete implementation for electric meters. Provides methods to retrieve usage data at various intervals (monthly, daily, hourly, 15-minute) for specified date ranges.

### Responsibilities
- Validate date ranges for electric meter queries
- Translate interval types to API mode codes
- Handle API quirks specific to each interval type:
  - Monthly: Returns all billing periods, requires client-side filtering
  - Daily: Returns 30-day windows, may require multiple API calls
  - Hourly/15min: Requires one API call per day
- Parse and normalize API response data
- Return data in consistent, pythonic format

### Public Interface

```python
from datetime import date, datetime
from typing import Optional, Iterator
from dataclasses import dataclass

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

class CpauElectricMeter(CpauMeter):
    """
    Represents a CPAU electric meter and provides methods to retrieve usage data.

    Supports four interval types:
    - monthly: Billing period data (roughly monthly)
    - daily: Daily aggregated usage
    - hourly: Hourly usage data
    - 15min: 15-minute interval usage data
    """

    def get_available_intervals(self) -> list[str]:
        """
        Get list of supported interval types for electric meters.

        Returns:
            ['monthly', 'daily', 'hourly', '15min']
        """
        pass

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
        pass

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
        pass

    def get_daily_usage(
        self,
        start_date: date,
        end_date: Optional[date] = None
    ) -> list[UsageRecord]:
        """
        Retrieve daily usage data.

        Convenience method equivalent to get_usage(interval='daily', ...)
        """
        pass

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
        pass

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
        pass

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
        pass

    @property
    def rate_category(self) -> str:
        """Get the rate category/schedule for this meter."""
        pass
```

---

## Class: CpauWaterMeter

### Purpose
Concrete implementation for water meters. Provides methods to retrieve water usage data at various intervals (billing, monthly, daily, hourly) for specified date ranges. Unlike electric meters, water meters use the WaterSmart portal which requires SAML/SSO authentication.

### Responsibilities
- Authenticate via SAML/SSO using Playwright browser automation
- Cache authentication cookies for fast re-authentication (~1s vs ~15s)
- Validate date ranges for water meter queries
- Translate interval types to WaterSmart API parameters
- Parse and normalize WaterSmart API response data
- Return data in consistent format compatible with electric meter interface

### Public Interface

```python
from datetime import date
from typing import Optional

class CpauWaterMeter(CpauMeter):
    """
    Represents a CPAU water meter accessed via the WaterSmart portal.

    Water meters require SAML/SSO authentication through the CPAU portal,
    which redirects to WaterSmart. This class handles the authentication
    automatically using Playwright and caches session cookies for fast
    re-authentication.

    Supports four interval types:
    - billing: Billing period data
    - monthly: Monthly aggregated usage
    - daily: Daily usage data
    - hourly: Hourly usage data
    """

    def __init__(
        self,
        username: str,
        password: str,
        cache_dir: str = "~/.cpau",
        timeout: int = 30000
    ):
        """
        Initialize a water meter instance with automatic authentication.

        Args:
            username: CPAU account username/email
            password: CPAU account password
            cache_dir: Directory for caching authentication cookies (default: ~/.cpau)
            timeout: Playwright timeout in milliseconds (default: 30000)

        Raises:
            CpauAuthenticationError: If SAML/SSO authentication fails
            CpauConnectionError: If unable to connect to portals

        Notes:
            - First authentication takes ~15 seconds (Playwright/SAML flow)
            - Subsequent authentications use cached cookies (~1 second)
            - Cookies are valid for ~10 minutes
        """
        pass

    def get_available_intervals(self) -> list[str]:
        """
        Get list of supported interval types for water meters.

        Returns:
            ['billing', 'monthly', 'daily', 'hourly']
        """
        pass

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
            Note: Water usage is returned in the import_kwh field (gallons, not kWh)

        Raises:
            ValueError: If interval is invalid or date range is invalid
            CpauApiError: If API request fails

        Notes:
            - Billing data typically available back to 2017
            - Hourly data available for last ~3 months
            - Water usage returned in gallons via the import_kwh field
            - export_kwh and net_kwh fields are zero for water data
        """
        pass

    def get_billing_usage(
        self,
        start_date: date,
        end_date: Optional[date] = None
    ) -> list[UsageRecord]:
        """
        Retrieve billing period water usage data.

        Convenience method equivalent to get_usage(interval='billing', ...)
        """
        pass

    def get_monthly_usage(
        self,
        start_date: date,
        end_date: Optional[date] = None
    ) -> list[UsageRecord]:
        """
        Retrieve monthly aggregated water usage.

        Convenience method equivalent to get_usage(interval='monthly', ...)
        """
        pass

    def get_daily_usage(
        self,
        start_date: date,
        end_date: Optional[date] = None
    ) -> list[UsageRecord]:
        """
        Retrieve daily water usage data.

        Convenience method equivalent to get_usage(interval='daily', ...)
        """
        pass

    def get_hourly_usage(
        self,
        start_date: date,
        end_date: Optional[date] = None
    ) -> list[UsageRecord]:
        """
        Retrieve hourly water usage data.

        Convenience method equivalent to get_usage(interval='hourly', ...)

        Note: Hourly data typically only available for last 3 months.
        """
        pass

    def get_availability_window(self, interval: str) -> tuple[date, date]:
        """
        Get the date range for which data is available for a given interval.

        Args:
            interval: One of 'billing', 'monthly', 'daily', 'hourly'

        Returns:
            Tuple of (earliest_date, latest_date) for available data

        Notes:
            - Billing/monthly/daily: typically back to 2017
            - Hourly: typically last 3 months
        """
        pass
```

### Implementation Notes

**Authentication Flow:**
1. Check cookie cache for valid session
2. If cached cookies exist and are fresh (< 10 minutes), use them
3. Otherwise, launch Playwright browser in headless mode
4. Navigate to CPAU portal and authenticate
5. Follow SAML redirect to WaterSmart portal
6. Extract session cookies and cache them
7. Use cookies for API requests

**API Characteristics:**
- WaterSmart uses REST API with JSON responses
- Different endpoint structure than electric meter
- Returns water consumption in gallons
- Data availability varies by interval type
- No 15-minute interval support

**Data Mapping:**
- Water consumption (gallons) → UsageRecord.import_kwh field
- export_kwh and net_kwh always zero for water data
- This allows unified interface with electric meters

---

## Exception Hierarchy

```python
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
```

---

## Usage Examples

### Basic Usage

```python
from cpau import CpauApiSession
from datetime import date

# Create session and login
with CpauApiSession(userid='myuser', password='mypass') as session:
    # Get the electric meter
    meter = session.get_electric_meter()

    # Get monthly usage for 2024
    monthly_data = meter.get_monthly_usage(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31)
    )

    # Print results
    for record in monthly_data:
        print(f"{record.date}: {record.net_kwh} kWh (net)")
```

### Retrieving Hourly Data

```python
from cpau import CpauApiSession
from datetime import date

with CpauApiSession(userid='myuser', password='mypass') as session:
    meter = session.get_electric_meter()

    # Get hourly data for a specific week
    hourly_data = meter.get_hourly_usage(
        start_date=date(2024, 12, 1),
        end_date=date(2024, 12, 7)
    )

    # Process hourly data
    for record in hourly_data:
        print(f"{record.date}: Import={record.import_kwh}, Export={record.export_kwh}")
```

### Streaming Large Date Ranges

```python
from cpau import CpauApiSession
from datetime import date

with CpauApiSession(userid='myuser', password='mypass') as session:
    meter = session.get_electric_meter()

    # Stream daily data for an entire year without loading into memory
    for record in meter.iter_usage(
        interval='daily',
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31)
    ):
        # Process one record at a time
        process_record(record)
```

### Multiple Meters

```python
from cpau import CpauApiSession

with CpauApiSession(userid='myuser', password='mypass') as session:
    # Get all electric meters (typically just one, but API supports multiple)
    meters = session.get_electric_meters()

    for meter in meters:
        print(f"Meter {meter.meter_number} at {meter.address}")
        data = meter.get_monthly_usage(start_date=date(2024, 1, 1))
        print(f"  Records: {len(data)}")
```

### Water Meter - Basic Usage

```python
from cpau import CpauWaterMeter
from datetime import date

# Create water meter (handles SAML/SSO authentication automatically)
meter = CpauWaterMeter(
    username='myuser@example.com',
    password='mypass',
    cache_dir='~/.cpau'  # Optional: cache cookies for fast re-auth
)

# Get daily water usage for December 2024
daily_data = meter.get_daily_usage(
    start_date=date(2024, 12, 1),
    end_date=date(2024, 12, 31)
)

# Water usage is in the import_kwh field (gallons, not kWh)
for record in daily_data:
    print(f"{record.date}: {record.import_kwh} gallons")
```

### Water Meter - Hourly Data

```python
from cpau import CpauWaterMeter
from datetime import date

meter = CpauWaterMeter(username='myuser', password='mypass')

# Get hourly water usage (typically available for last 3 months)
hourly_data = meter.get_hourly_usage(
    start_date=date(2024, 12, 1),
    end_date=date(2024, 12, 7)
)

for record in hourly_data:
    print(f"{record.date}: {record.import_kwh} gallons")
```

### Water Meter - Billing Periods

```python
from cpau import CpauWaterMeter
from datetime import date

meter = CpauWaterMeter(username='myuser', password='mypass')

# Get billing period data (available back to ~2017)
billing_data = meter.get_billing_usage(
    start_date=date(2024, 1, 1),
    end_date=date(2024, 12, 31)
)

for record in billing_data:
    print(f"{record.date}: {record.import_kwh} gallons")
```

### Water Meter - Check Data Availability

```python
from cpau import CpauWaterMeter

meter = CpauWaterMeter(username='myuser', password='mypass')

# Check what data is available for hourly interval
earliest, latest = meter.get_availability_window('hourly')
print(f"Hourly water data available from {earliest} to {latest}")

# Check billing data availability
earliest, latest = meter.get_availability_window('billing')
print(f"Billing data available from {earliest} to {latest}")
```

---

## Implementation Notes

### API Quirks to Handle

1. **Monthly Data**: API returns all billing periods regardless of date parameters. Client-side filtering required.

2. **Daily Data**: API returns 30-day windows ending on `strDate`. For ranges > 30 days, multiple API calls are needed, working backwards from end date.

3. **Hourly/15min Data**: API only supports single day per request. Requires one API call per day in range.

4. **CSRF Tokens**: Must be extracted from page HTML and included in API request headers.

5. **Date Formats**: API expects MM/DD/YY format but library should expose pythonic `date` objects.

### Data Normalization

- API returns separate records for import (IUsage) and export (Eusage)
- Library should combine these into single records with both values
- Calculate net usage (import - export) automatically
- Convert all dates to ISO format / datetime objects

### Error Handling

- Validate date ranges before making API calls
- Detect and report session expiration
- Provide clear error messages for common issues
- Log API interactions for debugging (when logging enabled)

---

## File Organization

Current module structure:

```
cpau/
    __init__.py                # Exports CpauApiSession, CpauElectricMeter,
                               # CpauWaterMeter, exceptions
    session.py                 # CpauApiSession implementation (electric meter)
    meter.py                   # CpauMeter base class
    electric_meter.py          # CpauElectricMeter implementation
    water_meter.py             # CpauWaterMeter implementation
    watersmart_session.py      # SAML/SSO authentication for WaterSmart
    exceptions.py              # Exception classes
    cli.py                     # CLI implementations (cpau-electric, cpau-water)
    baseapp.py                 # CLI application framework
```

---

## Future Extensions

### Potential Enhancements

**Gas Meter Support**: If CPAU adds gas service in the future, the `CpauMeter` base class architecture supports adding a `CpauGasMeter` class.

**Unified Session for Water**: Currently `CpauWaterMeter` is standalone. A future enhancement could integrate it with `CpauApiSession` to provide a unified entry point for all meter types.

**Enhanced Caching**: The water meter cookie cache could be extended to support longer-lived refresh tokens if the WaterSmart API provides them.

**Async Support**: Add async/await versions of data retrieval methods for better performance in async applications.

---

## CLI Implementation

Both CLI tools (`cpau-electric` and `cpau-water`) are thin wrappers around the library:

**Electric Meter CLI:**
```python
from cpau import CpauApiSession
from baseapp import BaseApp
import csv
import sys

class CpauElectricCli(BaseApp):
    def go(self, argv):
        # Parse arguments
        # ...

        # Use library
        with CpauApiSession(userid, password) as session:
            meter = session.get_electric_meter()
            data = meter.get_usage(interval, start_date, end_date)

            # Write CSV output
            writer = csv.DictWriter(sys.stdout, fieldnames=...)
            writer.writeheader()
            for record in data:
                writer.writerow({
                    'date': record.date,
                    'import_kwh': record.import_kwh,
                    # ...
                })
```

**Water Meter CLI:**
```python
from cpau import CpauWaterMeter
from baseapp import BaseApp
import csv
import sys

class CpauWaterCli(BaseApp):
    def go(self, argv):
        # Parse arguments
        # ...

        # Use library
        meter = CpauWaterMeter(username, password, cache_dir)
        data = meter.get_usage(interval, start_date, end_date)

        # Write CSV output
        writer = csv.DictWriter(sys.stdout, fieldnames=['date', 'gallons'])
        writer.writeheader()
        for record in data:
            writer.writerow({
                'date': record.date,
                'gallons': record.import_kwh  # Water data in import_kwh field
            })
```

This separation enables:
- Using the API from other Python scripts
- Testing the API independently from the CLI
- Building alternative interfaces (web app, GUI, etc.)
- Easier maintenance and evolution of both components
- Unified interface for both electric and water data
