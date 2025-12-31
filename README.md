# CPAU - City of Palo Alto Utilities Data Access

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Documentation Status](https://readthedocs.org/projects/cpau/badge/?version=latest)](https://cpau.readthedocs.io/en/latest/?badge=latest)

A Python library and CLI tools for downloading electric and water meter data from the City of Palo Alto Utilities (CPAU) customer portal.

## Overview

This library provides programmatic access to your historical electricity and water usage data from CPAU's customer portals:
- **Electric meter data**: From the [CPAU customer portal](https://mycpau.cityofpaloalto.org/Portal/Usages.aspx)
- **Water meter data**: From the [WaterSmart portal](https://paloalto.watersmart.com)

Since CPAU doesn't provide a public API, this library reverse-engineers the web portals' internal APIs to retrieve your data programmatically.

## Features

- ✅ **Python Library**: Clean, pythonic API for accessing CPAU data in your applications
- ✅ **CLI Tools**: Command-line interfaces for electric (`cpau-electric`), water (`cpau-water`), and availability (`cpau-availability`) data
- ✅ **Multiple Intervals**: Billing periods, monthly, daily, hourly, and 15-minute data
- ✅ **CSV Output**: Standard CSV format for easy data analysis
- ✅ **Type Hints**: Full type annotations for better IDE support
- ✅ **Cookie Caching**: Fast authentication (~1s) for repeated water meter queries
- ✅ **Data Availability Checks**: Discover what data ranges are available for your meters

## Installation

### From PyPI (when published)

```bash
pip install cpau

# For water meter support, install Playwright browser
playwright install chromium
```

### From GitHub (current)

```bash
pip install git+https://github.com/jsinnott/cpau.git

# For water meter support
playwright install chromium
```

### For Development

```bash
git clone https://github.com/jsinnott/cpau.git
cd cpau
pip install -e .
playwright install chromium  # For water meter support
```

**Note**: Water meter features require Playwright for SAML/SSO authentication. The `playwright install chromium` command downloads a headless Chromium browser (~100MB). Skip this if you only need electric meter data.

## Quick Start

### 1. Set Up Credentials

Create a `secrets.json` file with your CPAU login credentials:

```json
{
    "userid": "your_email@example.com",
    "password": "your_password"
}
```

⚠️ **Important**: Never commit this file to version control. It's already in `.gitignore`.

### 2. Use the CLI

```bash
# Electric meter - get daily usage for a date range
cpau-electric --interval daily 2024-12-01 2024-12-31 > electric_daily.csv

# Water meter - get hourly usage
cpau-water --interval hourly 2024-12-01 2024-12-31 > water_hourly.csv
```

### 3. Use the Library

```python
from cpau import CpauApiSession
from datetime import date

# Electric meter
with CpauApiSession(userid='your_email', password='your_password') as session:
    meter = session.get_electric_meter()
    data = meter.get_usage(
        interval='daily',
        start_date=date(2024, 12, 1),
        end_date=date(2024, 12, 31)
    )

    for record in data:
        print(f"{record.date}: {record.net_kwh} kWh")
```

## CLI Usage

### Electric Meter

```bash
# Daily data for a specific date range
cpau-electric --interval daily 2024-12-15 2024-12-20 > usage.csv

# Hourly data (end date defaults to 2 days ago if omitted)
cpau-electric --interval hourly 2024-12-17 > hourly.csv

# 15-minute interval data
cpau-electric --interval 15min 2024-12-17 2024-12-18 > detailed.csv

# Billing period data
cpau-electric --interval billing 2024-01-01 > billing.csv

# With verbose logging
cpau-electric -v --interval daily 2024-12-01 2024-12-31 > usage.csv
```

### Water Meter

```bash
# Daily water usage
cpau-water --interval daily 2024-12-01 2024-12-10 > water_usage.csv

# Hourly water data (end date defaults to today if omitted)
cpau-water --interval hourly 2024-12-01 > water_hourly.csv

# Monthly aggregated usage
cpau-water --interval monthly 2024-09-01 2024-11-30 > water_monthly.csv

# Billing period data
cpau-water --interval billing 2024-01-01 2024-12-31 > water_billing.csv

# Custom cache directory for authentication cookies
cpau-water --cache-dir /tmp/cpau-cache --interval daily 2024-12-01 > water.csv
```

### Data Availability

```bash
# Check what data is available for your meters
cpau-availability > availability.csv

# With verbose logging to see progress
cpau-availability -v > availability.csv

# Save to file
cpau-availability --output-file availability.csv
```

The output shows available date ranges for each meter type and interval:

```csv
data_type,interval,data_start,data_end
electric,billing,2020-01-01,2024-12-31
electric,monthly,2020-01-01,2024-12-31
electric,daily,2020-01-01,2024-12-31
electric,hourly,2024-10-01,2024-12-31
electric,15min,2024-10-01,2024-12-31
water,billing,2017-01-01,2024-12-31
water,monthly,2017-01-01,2024-12-31
water,daily,2017-01-01,2024-12-31
water,hourly,2024-10-01,2024-12-31
```

**Note**: This command checks both electric and water meters. If one meter fails (e.g., authentication issues), it will still report data for the other meter. The command only fails if both meters fail or no data is available.

### Command Options

**cpau-electric and cpau-water:**
- **start_date** (required): Start date in YYYY-MM-DD format
- **end_date** (optional): End date in YYYY-MM-DD format
  - Electric meter: defaults to 2 days ago
  - Water meter: defaults to today
- `--interval, -i`: Time granularity (default: `billing`)
  - Electric: `billing`, `monthly`, `daily`, `hourly`, `15min`
  - Water: `billing`, `monthly`, `daily`, `hourly`
- `--secrets-file`: Path to credentials file (default: `secrets.json`)
- `--output-file, -o`: Write to file instead of stdout
- `--cache-dir`: Cookie cache directory for water meter (default: `~/.cpau`)
- `--verbose, -v`: Enable verbose debug logging
- `--silent, -s`: Suppress all log output

**cpau-availability:**
- `--secrets-file`: Path to credentials file (default: `secrets.json`)
- `--cache-dir`: Cookie cache directory for water meter (default: `~/.cpau`)
- `--output-file, -o`: Write to file instead of stdout
- `--verbose, -v`: Enable verbose debug logging
- `--silent, -s`: Suppress all log output

## Python Library API

### Electric Meter

```python
from cpau import CpauApiSession
from datetime import date

# Create session (use with context manager for automatic cleanup)
with CpauApiSession(userid='your_email', password='your_password') as session:
    # Get the electric meter
    meter = session.get_electric_meter()

    # Get usage data for any interval type
    records = meter.get_usage(
        interval='daily',  # or 'billing', 'monthly', 'hourly', '15min'
        start_date=date(2024, 12, 1),
        end_date=date(2024, 12, 31)
    )

    # Process the data
    for record in records:
        print(f"{record.date}: Import={record.import_kwh} kWh, "
              f"Export={record.export_kwh} kWh, Net={record.net_kwh} kWh")

    # Check data availability
    earliest, latest = meter.get_availability_window('daily')
    print(f"Daily data available from {earliest} to {latest}")
```

### Water Meter

```python
from cpau import CpauWaterMeter
from datetime import date

# Create water meter (handles SAML/SSO authentication automatically)
meter = CpauWaterMeter(
    username='your_email',
    password='your_password',
    cache_dir='~/.cpau'  # Optional: cache cookies for fast re-auth
)

# Get usage data
records = meter.get_usage(
    interval='daily',  # or 'billing', 'monthly', 'hourly'
    start_date=date(2024, 12, 1),
    end_date=date(2024, 12, 31)
)

# Water usage is in the import_kwh field (gallons, not kWh)
for record in records:
    print(f"{record.date}: {record.import_kwh} gallons")

# Check data availability
earliest, latest = meter.get_availability_window('daily')
print(f"Water data available from {earliest} to {latest}")
```

## Output Format

All commands output CSV data with dates in ISO format (timezone-naive):

**Daily Electric Data:**
```csv
date,export_kwh,import_kwh,net_kwh
2024-12-15,0.1,28.06,27.96
2024-12-16,1.43,22.25,20.82
```

**Hourly Data:**
```csv
date,export_kwh,import_kwh,net_kwh
2024-12-17 00:00:00,0.0,0.58,0.58
2024-12-17 01:00:00,0.0,0.64,0.64
```

**Billing Period Data:**
```csv
date,billing_period_start,billing_period_end,billing_period_length,export_kwh,import_kwh,net_kwh
2024-12-01,2024-12-01,2024-12-31,31,156.2,689.4,533.2
```

**Water Data:**
```csv
date,gallons
2024-12-01,168.309
2024-12-02,222.169
```

### Data Fields

**Electric Meter:**
- **export_kwh**: Solar generation sent to grid (for NEM 2.0 customers)
- **import_kwh**: Electricity consumed from grid
- **net_kwh**: Import - Export (positive = net consumption)

**Water Meter:**
- **gallons**: Water consumption in gallons (stored in `import_kwh` field)

## Performance

**Electric Meter:**
- Authentication: ~2 seconds
- Monthly/Billing: ~1-2 seconds (single API call)
- Daily (≤30 days): ~1-2 seconds (single API call)
- Hourly/15-min: ~0.5 seconds per day

**Water Meter:**
- First authentication: ~15 seconds (Playwright/SAML)
- Cached authentication: ~1 second (10-minute cache window)
- Data retrieval: ~1 second per API call

## Data Availability

**Electric Meter:**
- Historical data available back to your account creation
- Recent data has ~2 day delay (end date must be ≥2 days ago)

**Water Meter:**
- Billing data: Available back to 2017 for most accounts
- Hourly data: Available for last 3 months
- Data generally available through today for most intervals

## How It Works

### Electric Meter

The library makes direct HTTP API calls to the CPAU portal's internal endpoints:

1. Establishes session and extracts CSRF token from login page
2. Authenticates with credentials and CSRF token
3. Retrieves meter information from `/Portal/Usages.aspx/BindMultiMeter`
4. Fetches usage data from `/Portal/Usages.aspx/LoadUsage`

### Water Meter

The library uses Playwright for SAML/SSO authentication:

1. Opens headless browser and navigates to CPAU portal
2. Logs in and follows SAML redirect to WaterSmart
3. Extracts session cookies and caches them (10-minute validity)
4. Makes authenticated API calls to WaterSmart REST endpoints
5. Reuses cached cookies for subsequent invocations (fast!)

## Troubleshooting

### "Error: invalid start date format"
Dates must be in `YYYY-MM-DD` format:
- ✅ Correct: `2024-12-17`
- ❌ Wrong: `12/17/24`, `2024/12/17`

### "Error: end date cannot be later than 2 days ago"
Electric meter data has a ~2 day delay. If today is December 23, you can request data through December 21.

### "Error: secrets.json not found"
Create a `secrets.json` file with your CPAU credentials (see Quick Start above).

### Water meter authentication timeout
Try increasing the timeout or running with `--verbose` to see detailed logs:
```bash
cpau-water -v --interval daily 2024-12-01 > output.csv
```

### No data returned
- Verify you can log in manually at the CPAU portal
- Check that the date range is within the data availability window
- Use `--verbose` to see detailed API responses

## Repository Structure

```
cpau/
├── src/cpau/              # Main library package
│   ├── __init__.py        # Public API exports
│   ├── cli.py             # Command-line interfaces
│   ├── session.py         # Electric meter session
│   ├── electric_meter.py  # Electric meter API
│   ├── water_meter.py     # Water meter API
│   ├── watersmart_session.py  # SAML/SSO authentication
│   ├── meter.py           # Base meter classes
│   ├── baseapp.py         # CLI application framework
│   └── exceptions.py      # Custom exceptions
│
├── docs/                  # Documentation
│   ├── api_design.md      # API design document
│   └── development_history.org  # Development notes
│
├── dev-tools/             # Development scripts (not in package)
│   ├── electric/          # Scripts for reverse-engineering electric API
│   └── water/             # Scripts for reverse-engineering water API
│
├── pyproject.toml         # Package configuration
├── README.md              # This file
├── LICENSE                # MIT License
└── .gitignore             # Git ignore rules
```

## Development

Contributions welcome! This project was developed through reverse-engineering the CPAU customer portals. See `docs/development_history.org` for the full development journey.

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Manual integration tests (require valid credentials)
python dev-tools/electric/test_cpau_api.py
python dev-tools/water/test_cookies_with_requests.py
```

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Disclaimer

This is an unofficial tool developed by reverse-engineering the CPAU customer portals. It is not affiliated with, endorsed by, or supported by the City of Palo Alto or City of Palo Alto Utilities.

Use at your own risk. The library may break if CPAU changes their portal structure or APIs.

## Acknowledgments

Developed through systematic experimentation and reverse-engineering of the CPAU customer portals. Special thanks to the Claude AI assistant for helping navigate the authentication flows and API quirks.

For the full development story, including all the dead ends and breakthroughs, see [docs/development_history.org](docs/development_history.org).
