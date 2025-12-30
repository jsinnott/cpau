# CPAU Meter Data Scraper

A Python script to automatically download electric meter data from the City of Palo Alto Utilities (CPAU) customer portal.

## Project Goal

Automate the download of historical electricity usage data from the CPAU customer portal at https://mycpau.cityofpaloalto.org/Portal/Usages.aspx. The utility does not provide a public API, so this tool reverse-engineers the web portal's internal API calls to retrieve data programmatically.

## Quick Start

### Installation

1. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `secrets.json` file with your CPAU login credentials:
```json
{
    "userid": "your_email@example.com",
    "password": "your_password"
}
```

### Usage

The script requires a start date and optionally accepts an end date (defaults to 2 days ago):

```bash
# Get daily data for a specific date range
python3 cpau_download.py 2025-12-15 2025-12-20 --interval daily > usage.csv

# Get hourly data for a single day (end date defaults to 2 days ago if omitted)
python3 cpau_download.py 2025-12-17 --interval hourly > hourly.csv

# Get 15-minute interval data for multiple days
python3 cpau_download.py 2025-12-17 2025-12-18 --interval 15min > detailed.csv

# Get monthly billing data (requires date arguments to filter billing periods)
python3 cpau_download.py 2025-01-01 --interval monthly > monthly.csv
```

**Date Format**: All input dates must be in `YYYY-MM-DD` format (e.g., `2025-12-17`)

**Important**: Due to data availability delays in the CPAU system, the end date cannot be later than 2 days ago. Hourly and 15-minute data typically has a 2-day lag before becoming available.

### Command-Line Options

- **start_date** (required): Start date in YYYY-MM-DD format
- **end_date** (optional): End date in YYYY-MM-DD format (defaults to 2 days ago)
- `--interval`: Time granularity - `monthly`, `daily`, `hourly`, or `15min` (default: monthly)
- `--secrets-file`: Path to credentials file (default: secrets.json)
- `--output-file`: Write output to file instead of stdout
- `-v, --verbose`: Enable verbose debug logging
- `-s, --silent`: Suppress all log output

### Output Format

The script outputs CSV data to stdout with dates in ISO format (timezone-naive). The exact columns depend on the interval type:

**Monthly Data:**
```csv
date,billing_period,export_kwh,import_kwh,net_kwh
2024-11,10/11/24 to 11/12/24,199.0,513.0,314.0
2024-12,11/13/24 to 12/10/24,116.0,519.0,403.0
2025-01,12/11/24 to 01/13/25,112.0,666.0,554.0
```
- `date`: YYYY-MM format
- `billing_period`: Original format from CPAU (not converted to ISO)

**Daily Data:**
```csv
date,export_kwh,import_kwh,net_kwh
2025-12-15,0.1,28.06,27.96
2025-12-16,1.43,22.25,20.82
2025-12-17,0.44,33.63,33.19
```
- `date`: YYYY-MM-DD format

**Hourly Data:**
```csv
date,export_kwh,import_kwh,net_kwh
2025-12-17 00:00:00,0.0,0.58,0.58
2025-12-17 01:00:00,0.0,0.64,0.64
2025-12-17 02:00:00,0.0,0.65,0.65
```
- `date`: YYYY-MM-DD HH:MM:SS format

**15-Minute Data:**
```csv
date,export_kwh,import_kwh,net_kwh
2025-12-17 00:00:00,0.0,0.15,0.15
2025-12-17 00:15:00,0.0,0.14,0.14
2025-12-17 00:30:00,0.0,0.14,0.14
```
- `date`: YYYY-MM-DD HH:MM:SS format

Progress messages are logged to stderr, so you can safely redirect stdout to a file.

### Data Meanings

- **Export kWh**: Solar generation sent to the grid (for NEM 2.0 customers)
- **Import kWh**: Electricity consumed from the grid
- **Net kWh**: Import - Export (positive means net consumption)

## How It Works

The script uses the Python `requests` library to make direct HTTP calls to the portal's internal APIs. This approach was chosen over browser automation for better performance and simpler dependencies.

### Architecture

The script uses a `BaseApp` architecture that provides:
- Standard argument parsing with automatic logging of all options
- Configurable logging (INFO, DEBUG levels)
- Consistent error handling and exit codes
- Reusable infrastructure for similar utility scrapers

### Authentication Flow

1. **Initial Session**: GET request to the portal homepage establishes session cookies
2. **Extract CSRF Token**: Parse `__RequestVerificationToken` from homepage HTML
3. **Login**: POST to `/Portal/Default.aspx/validateLogin` with credentials and CSRF token
4. **Page Load**: GET request to `/Portal/Usages.aspx` to establish authenticated session state
5. **Extract API Token**: Parse `ctl00$hdnCSRFToken` from Usages page HTML
6. **Data Retrieval**: Make authenticated API calls with API token in `csrftoken` header

### API Endpoints

The script calls two key endpoints:

1. **`/Portal/Usages.aspx/BindMultiMeter`**
   - Payload: `{"MeterType": "E"}`
   - Returns: List of meters associated with the account
   - Used to identify the active meter number

2. **`/Portal/Usages.aspx/LoadUsage`**
   - Payload: Meter number plus parameters for interval mode and date range
   - Returns: Usage data at the requested granularity
   - Supports modes: M (monthly), D (daily), H (hourly), MI (15-minute)

### Interval Modes and API Behavior

The CPAU API supports four time granularities with different behaviors:

| Interval | API Mode | Date Parameter Behavior | Records/Call | Multi-Day Strategy |
|----------|----------|------------------------|--------------|-------------------|
| monthly  | M        | Dates ignored; returns all billing periods | All available | Filter client-side |
| daily    | D        | `strDate` = end date; returns 30 days ending on that date | 30 days | Multiple calls for >30 day ranges |
| hourly   | H        | `strDate` = specific day; returns hourly data for that day only | 24 hours | One call per day |
| 15min    | MI       | `strDate` = specific day; returns 15-min data for that day only | 96 intervals | One call per day |

**Key Discovery**: The API completely ignores the `DateFromDaily` and `DateToDaily` parameters. Only the `strDate` parameter controls which data is returned.

### Date Range Handling

**Monthly Mode**:
- Makes a single API call that returns all billing periods
- Filters results to only include billing periods that overlap with the requested date range
- Overlap logic: includes period if `period_end >= start_date AND period_start <= end_date`

**Daily Mode**:
- For ranges ≤ 30 days: Single API call with `strDate` set to end date
- For ranges > 30 days: Multiple API calls in 30-day chunks, working backwards from end date
- Client-side filtering to exact requested range

**Hourly/15-Minute Modes**:
- Makes one API call per day in the requested range
- Each call uses `strDate` to specify a single day
- Results are combined into a single dataset

### Data Availability

Through systematic testing, we discovered:
- **Monthly data**: Available immediately for completed billing periods
- **Daily data**: Available for recent dates including yesterday
- **Hourly/15-minute data**: Has approximately a 2-day lag before becoming available

The script enforces that the end date cannot be later than 2 days ago to prevent requests for unavailable data.

### Date Format Conversions

The API uses `MM/DD/YY` format (2-digit year), but the script handles conversions:

**Input** (user-facing):
- YYYY-MM-DD format for all date arguments
- Example: `2025-12-17`

**Internal** (API communication):
- Converted to MM/DD/YY format
- Example: `12/17/25`

**Output** (CSV data):
- ISO format (timezone-naive)
- Daily: `2025-12-17`
- Hourly/15-min: `2025-12-17 14:30:00`
- Monthly date column: `2025-11`
- Monthly billing_period: Original format preserved

## Development Journey

The repository contains experimental scripts (now organized in `dev-tools/electric/` and `test/electric/`) created during two development phases:

### Phase 1: Initial Development (Basic Monthly Data)

1. **`scrape_cpau.py`** - Initial Playwright-based browser automation
2. **`analyze_api.py`** - API response structure analysis
3. **`debug_login.py`** - Login request format discovery
4. **`test_api.py`** - Direct API call experimentation
5. **`capture_requests.py`** - API payload capture
6. **`find_csrf_token.py`** - **Breakthrough**: Discovered CSRF token in `ctl00$hdnCSRFToken`
7. **`cpau_download.py`** - Initial working implementation

### Phase 2: Enhancements (Multiple Intervals, Dates, CSV Output)

8. **`explore_intervals_auto.py`** - Automated UI exploration to find interval controls
9. **`capture_all_intervals.py`** - Captured API requests for all interval modes (M, D, H, MI)
10. **`test_date_ranges.py`** - Tested date format requirements (discovered MM/DD/YY)
11. **`inspect_daily_data.py`** - Analyzed daily data record structure
12. **`inspect_hourly.py`** - Examined hourly data structure
13. **`test_data_availability.py`** - Tested data availability across different dates
14. **`test_payload_variations.py`** - **Breakthrough**: Systematically tested payload combinations; discovered `DateFromDaily`/`DateToDaily` are ignored
15. **`test_api_dates.py`** - Confirmed API ignores date range parameters
16. **`test_strdate_param.py`** - Discovered `strDate` controls which data is returned
17. **`test_hourly_date_params.py`** - Confirmed hourly/15-min only support single days per call

Key discoveries from Phase 2:
- Interval modes: M (monthly), D (daily), H (hourly), MI (15-minute)
- Date format requirement: MM/DD/YY with 2-digit year for API
- `strDate` parameter behavior varies by mode
- `DateFromDaily`/`DateToDaily` are completely ignored
- Data grouping: Hourly and 15-minute records include `Hourly` field with time
- Data delay: ~2 day lag for hourly and 15-minute data availability
- Daily mode returns 30 days maximum per API call
- Monthly mode filtering must be done client-side

## Technical Details

### CSRF Token Discovery

A critical challenge was CSRF (Cross-Site Request Forgery) protection. The portal requires **two different CSRF tokens**:
1. **Login token**: From `__RequestVerificationToken` field on homepage
2. **API token**: From `ctl00$hdnCSRFToken` hidden field on Usages page

The breakthrough came from discovering that ASP.NET embeds the API token in a hidden input field rather than in JavaScript variables or cookies.

### Data Structure

The portal returns usage data with separate records for:
- **"Eusage"** (Export): Solar generation sent to grid (stored as negative, converted to positive)
- **"IUsage"** (Import): Electricity consumed from grid (positive values)

For each time interval (month/day/hour/15min), the script:
1. Groups records by time period
2. Sums export and import values separately
3. Calculates net = import - export

### Date Validation

The script validates dates to ensure:
- Start and end dates are in YYYY-MM-DD format
- End date >= start date
- End date is no later than 2 days ago (data availability constraint)
- Dates are valid calendar dates

Invalid dates or ranges produce clear error messages.

### Performance Characteristics

- **Monthly mode**: ~1-2 seconds (single API call regardless of date range)
- **Daily mode ≤ 30 days**: ~1-2 seconds (single API call)
- **Daily mode > 30 days**: ~2-3 seconds per 30-day chunk
- **Hourly mode**: ~0.5 seconds per day requested
- **15-minute mode**: ~0.5 seconds per day requested

## Repository Structure

The repository is organized to separate production code from development artifacts and testing scripts. The structure is designed to accommodate future expansion (e.g., water meter data download) while keeping the codebase clean and organized:

```
cpau-scrape/
├── cpau_download.py          # Main production script
├── baseapp.py                # Base application class (symlink)
├── requirements.txt          # Python dependencies
├── secrets.json              # User credentials (gitignored, must create manually)
├── README.md                 # This file
├── claude.org                # Project instructions and history
├── dev-tools/                # Development and exploration scripts
│   └── electric/             # Scripts used to develop electric meter downloader
│       ├── scrape_cpau.py
│       ├── analyze_api.py
│       ├── find_csrf_token.py
│       └── ...               # Other exploration scripts
└── test/                     # Test and validation scripts
    └── electric/             # Tests for electric meter functionality
        ├── test_api_dates.py
        ├── test_payload_variations.py
        └── ...               # Other test scripts
```

### Production Code
- **`cpau_download.py`** - Main script for downloading electric meter data
- **`baseapp.py`** - Base application class (symlink to external infrastructure)
- **`requirements.txt`** - Python dependencies
- **`secrets.json`** - User credentials (gitignored, must create manually)

### Documentation
- **`README.md`** - This file
- **`claude.org`** - Combined project instructions and development history

### Development Scripts (`dev-tools/electric/`)

Development scripts created during the exploration and implementation phases. These scripts were instrumental in understanding the CPAU API but are not needed for normal operation.

**Phase 1 Scripts:**
- **`scrape_cpau.py`** - Initial Playwright-based exploration
- **`analyze_api.py`** - API response capture and analysis
- **`debug_login.py`** - Login request format debugging
- **`capture_requests.py`** - API payload capture
- **`find_csrf_token.py`** - CSRF token location discovery (key breakthrough)

**Phase 2 Scripts:**
- **`explore_intervals_auto.py`** - UI control discovery for intervals
- **`capture_all_intervals.py`** - Interval mode API request capture
- **`inspect_daily_data.py`** - Daily data structure analysis
- **`inspect_hourly.py`** - Hourly data structure analysis

### Test Scripts (`test/electric/`)

Test scripts created to validate API behavior and discover correct parameter usage:

- **`test_date_ranges.py`** - Date format testing
- **`test_data_availability.py`** - Data availability testing across dates
- **`test_payload_variations.py`** - Systematic payload testing (key breakthrough)
- **`test_api_dates.py`** - API date parameter behavior analysis
- **`test_strdate_param.py`** - strDate parameter discovery
- **`test_hourly_date_params.py`** - Hourly/15-min date behavior testing

**Note:** All scripts in `dev-tools/` and `test/` directories reference `../../secrets.json` to access credentials from the repository root.

## Troubleshooting

### "Error: invalid start date format"
Dates must be in YYYY-MM-DD format. Examples:
- ✓ Correct: `2025-12-17`
- ✗ Wrong: `12/17/25`, `2025/12/17`, `17-12-2025`

### "Error: end date cannot be later than 2 days ago"
The CPAU system has a ~2 day delay before data becomes available. If today is 2025-12-23, you can request data up to 2025-12-21, but not 2025-12-22 or later.

### "Error: end date must be >= start date"
Check that your date range makes sense (end comes after start).

### "Error: secrets.json not found"
Create a `secrets.json` file in the project directory with your CPAU login credentials.

### "Error: Login failed"
- Verify your credentials in `secrets.json`
- Check if your account is locked (too many failed login attempts)
- Ensure you can log in manually through the website

### "Error: CSRF token not found in page"
The portal's HTML structure may have changed. The token is typically in a hidden field named `ctl00$hdnCSRFToken`. You may need to update the regex pattern in the `get_meter_data()` function.

### No data returned for hourly/15-minute intervals
Make sure you're requesting dates at least 2 days in the past. Recent data may not be available yet due to the CPAU system's processing delay.

### Daily mode returns wrong number of records
For date ranges longer than 30 days, the script makes multiple API calls and filters results. If you're getting unexpected results, try verbose mode (`-v`) to see the API calls being made.

## Dependencies

- **Python 3.7+**
- **requests** - For HTTP API calls
- **playwright** (optional) - Only needed for experimental/debugging scripts

## License

MIT License - Feel free to use and modify for your own utility data downloads.

## Acknowledgments

This project was developed through iterative experimentation and reverse engineering of the CPAU customer portal across two development phases:

- **Phase 1**: Established the basic authentication flow and monthly data retrieval
- **Phase 2**: Added multi-interval support, date range filtering, CSV output, and ISO date formatting

The progression from browser automation to direct API calls, and the discovery of the API's quirky date parameter behavior, demonstrates the value of systematic exploration when building automation tools for undocumented APIs.
