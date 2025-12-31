# Water Meter Authentication Flow Investigation

## Status: PHASES 1 & 2 COMPLETED ✓

Successfully explored watersmart.com authentication, discovered all water data APIs, and implemented session management with automatic cookie handling.

**Phase 1**: Authentication & API Discovery ✓
**Phase 2**: Session Management & Cookie Handling ✓
**Phase 3**: API Design & Implementation (NEXT)

## Key Finding

**Browser automation is required** - The SAML/SSO authentication flow requires JavaScript execution to auto-submit forms. The `requests` library alone is insufficient.

## Authentication Flow Discovered

### Step-by-Step Process

1. **Login to CPAU Portal**
   - URL: `https://mycpau.cityofpaloalto.org/Portal`
   - Username field: `#txtLogin`
   - Password field: `#txtpwd`
   - Submit: Press Enter on password field

2. **Navigate to Watersmart.com**
   - Access any `paloalto.watersmart.com` URL
   - Example: `https://paloalto.watersmart.com/index.php/trackUsage`

3. **SAML/SSO Redirect**
   - CPAU portal redirects to: `https://mycpau.cityofpaloalto.org/sso-watersmart/`
   - Server returns HTML with auto-submitting SAML form
   - Form targets: `https://paloalto.watersmart.com/saml/module.php/saml/sp/saml2-acs.php/paloaltoca_live`

4. **SAML Assertion Submission**
   - JavaScript auto-submits SAML response
   - User redirected to requested watersmart page
   - Session cookies established:
     - `PHPSESSID` (watersmart.com)
     - `SimpleSAMLSessionID` (watersmart.com)

5. **Authenticated Access**
   - Session cookies enable access to all watersmart APIs
   - No additional authentication needed for API calls

### SAML Details
- **Issuer**: `https://mycpau.cityofpaloalto.org/Portal`
- **Recipient**: `https://paloalto.watersmart.com`
- **Assertion includes**:
  - Account number: `30014771`
  - Customer ID: `001000570

6`
  - Email address
  - Valid time window (3 minutes)

## Discovered APIs

See **API_FINDINGS.md** for comprehensive documentation.

### Summary of Water Data APIs

All under base URL: `https://paloalto.watersmart.com/index.php/rest/v1/Chart/`

1. **weatherConsumptionChart** - Daily usage with weather correlation
2. **RealTimeChart** - Recent hourly data (~3 months)
3. **BillingHistoryChart** - Historical billing periods with cohort comparison
4. **yearOverYearChart** - Monthly usage by year
5. **annualChart** - Yearly totals with predictions
6. **usagePieChart** - Usage breakdown by category (irrigation, indoor, etc.)

All APIs:
- Return JSON format
- Use gallons as unit
- Wrapped in `{"data": {...}}` structure
- Require authenticated session cookies

## Tools Created

### 1. explore_auth_standalone.py
**Status**: Insufficient for the task
- Uses `requests` library only
- Cannot execute JavaScript
- Captures SAML forms but cannot submit them

### 2. explore_with_playwright.py
**Status**: WORKING ✓
- Uses Playwright for browser automation
- Logs in to CPAU portal
- Navigates through SAML flow
- Captures all API calls with responses
- Saves authenticated page HTML

**Usage**:
```bash
../../bin/python3 explore_with_playwright.py
```

## Files Generated

- `/tmp/watersmart_trackUsage_real.html` - Authenticated Track Usage page
- `/tmp/watersmart_download_real.html` - Authenticated Download page
- `/tmp/watersmart_api_calls.json` - Complete API call log with responses
- `/tmp/playwright_run.log` - Full execution log
- `API_FINDINGS.md` - Comprehensive API documentation

## Answers to Key Questions

### 1. Can we navigate directly to watersmart.com after CPAU login?
**No** - Must follow SAML redirect flow. Direct navigation triggers SSO authentication.

### 2. Is SAML/SSO being used?
**Yes** - Full SAML 2.0 implementation with signed assertions.

### 3. What cookies are required?
- `PHPSESSID` (paloalto.watersmart.com)
- `SimpleSAMLSessionID` (paloalto.watersmart.com)

After authentication, these cookies are sufficient for API access.

### 4. Can we programmatically access the APIs?
**Yes** - After obtaining session cookies through browser automation:
1. Authenticate using Playwright
2. Extract session cookies
3. Use cookies with `requests` library for API calls
4. Session appears to remain valid for extended period

## Data Availability

- **Hourly data**: ~3 months (RealTimeChart)
- **Daily data**: Several months (weatherConsumptionChart)
- **Billing period data**: Multiple years (2017+)
- **Annual data**: Multiple years

## Comparison to Electric Meter

| Feature | Electric Meter | Water Meter |
|---------|---------------|-------------|
| Authentication | Direct JSON POST | SAML/SSO via browser |
| Session | Simple cookies | SAML session cookies |
| API Type | Custom endpoints | RESTful chart APIs |
| Implementation | `requests` only | Playwright + `requests` |
| Complexity | Low | Medium-High |

## Phase 2: Session Management ✓ COMPLETED

See **PHASE2_SUMMARY.md** for complete details.

### Accomplishments
1. ✓ Validated hybrid approach (Playwright + requests)
2. ✓ Tested cookie lifetime (valid 10+ minutes)
3. ✓ Implemented `WatersmartSessionManager` class
4. ✓ Auto-refresh on 401 errors
5. ✓ Created comprehensive installation guide

### Key Deliverables
- **watersmart_session.py** - Production-ready session manager
- **PHASE2_FINDINGS.md** - Technical analysis
- **INSTALLATION_GUIDE.md** - User documentation
- **Test scripts** - Validation suite

### Performance
- First API call: ~15s (includes Playwright auth)
- Subsequent calls: <1s (reuses cookies)
- 66% faster with cookie reuse

## Next Steps (Phase 3)

### API Design & Implementation
1. Design `CpauWaterMeter` class interface
2. Match `CpauElectricMeter` API patterns
3. Parse API responses into `UsageRecord` objects
4. Implement interval handling (hourly, daily, monthly, billing)
5. Add availability window detection
6. Comprehensive error handling

### Class Interface (Draft)
```python
class CpauWaterMeter:
    def __init__(self, username, password, headless=True):
        """Initialize with CPAU credentials."""
        self._session_manager = WatersmartSessionManager(
            username, password, headless
        )

    def get_usage(self, start_date, end_date, interval='daily'):
        """Retrieve water usage data."""
        # Parse API responses
        # Return list of UsageRecord objects
        pass

    def get_availability_window(self, interval):
        """Find earliest and latest available dates."""
        pass

    def download_billing_data(self, output_path):
        """Download CSV of billing period data."""
        pass
```

## Environment Notes

- Python virtual environment working correctly
- Playwright installed and configured
- Chromium browser downloaded for Playwright
- All dependencies in `requirements.txt`

## References

- Electric meter scripts in `dev-tools/electric/` (esp. `scrape_cpau.py`)
- CPAU portal login fields match electric meter implementation
- SAML authentication is standard SAML 2.0 protocol
