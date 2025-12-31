# Watersmart.com API Findings

## Summary

Successfully explored the watersmart.com water meter data APIs using browser automation. The site uses SAML/SSO authentication through the CPAU portal, and provides several RESTful JSON APIs for chart data.

## Authentication

### SAML/SSO Flow
1. Login to CPAU portal at `https://mycpau.cityofpaloalto.org/Portal`
2. Navigate to any `paloalto.watersmart.com` URL
3. Server redirects to `https://mycpau.cityofpaloalto.org/sso-watersmart/` with SAML request
4. CPAU server responds with SAML assertion (auto-submitted form)
5. User is redirected to `https://paloalto.watersmart.com/saml/auth` with SAML response
6. Session cookies are established: `PHPSESSID` and `SimpleSAMLSessionID`

### Key Points
- **Cannot use simple requests library**: SAML flow requires JavaScript execution
- **Must use browser automation** (Playwright/Selenium) for authentication
- **Session persists**: Once authenticated, the session cookies work for subsequent API calls

## Discovered APIs

All APIs are under the base URL: `https://paloalto.watersmart.com/index.php/rest/v1/Chart/`

### 1. Weather Consumption Chart
**Endpoint**: `GET /rest/v1/Chart/weatherConsumptionChart?module=portal&commentary=full`

**Purpose**: Daily water consumption with weather correlation

**Data Structure**:
```json
{
  "data": {
    "chartData": {
      "mode": "ami",
      "dailyData": {
        "categories": ["2024-08-11", "2024-08-12", ...],
        "series": [...],
        "temperature": [...]
      }
    }
  }
}
```

**Notes**:
- Provides daily consumption data
- Includes temperature correlation
- Mode "ami" suggests Advanced Metering Infrastructure (hourly capable)

### 2. Real-Time Chart
**Endpoint**: `GET /rest/v1/Chart/RealTimeChart`

**Purpose**: Recent hourly usage data

**Data Structure**:
```json
{
  "data": {
    "series": [
      {
        "read_datetime": 1723334400,
        "gallons": 0,
        "flags": null
      },
      ...
    ]
  }
}
```

**Notes**:
- Unix timestamps for readings
- Gallons unit
- Flags field (purpose unknown - likely data quality indicators)
- Appears to show last ~3 months of hourly data

### 3. Billing History Chart
**Endpoint**: `GET /rest/v1/Chart/BillingHistoryChart?flowType=per_day&comparison=cohort`

**Purpose**: Billing period consumption with per-day normalization

**Query Parameters**:
- `flowType`: `per_day` (shows normalized daily average per billing period)
- `comparison`: `cohort` (compares to similar households)

**Data Structure**:
```json
{
  "data": {
    "chart_data": [
      {
        "consumption": null,
        "gallons": "9724.00",
        "color": "#5DC7D3",
        ...
      }
    ]
  }
}
```

**Notes**:
- Historical billing periods
- Can request total or per-day average
- Includes cohort comparison data

### 4. Year-Over-Year Chart
**Endpoint**: `GET /rest/v1/Chart/yearOverYearChart?module=portal&commentary=full`

**Purpose**: Monthly consumption by year for comparison

**Data Structure**:
```json
{
  "data": {
    "chartData": {
      "categories": ["<span isolate>Jan</span>", "<span isolate>Feb</span>", ...],
      "series": [
        {
          "name": "2024",
          "data": [...]
        },
        {
          "name": "2023",
          "data": [...]
        }
      ]
    }
  }
}
```

**Notes**:
- Monthly granularity
- Multiple years for comparison
- Categories include HTML markup (needs parsing)

### 5. Annual Chart
**Endpoint**: `GET /rest/v1/Chart/annualChart?module=portal&commentary=full`

**Purpose**: Yearly consumption totals with predictions

**Data Structure**:
```json
{
  "data": {
    "showPredicted": true,
    "chartData": {
      "2021": {
        "begin_date": "20210101",
        "end_date": "20211231",
        "gallons": ...,
        ...
      },
      "2022": {...},
      ...
    }
  }
}
```

**Notes**:
- Annual totals going back multiple years
- Includes predicted consumption for current year
- Date format: YYYYMMDD

### 6. Usage Pie Chart
**Endpoint**: `GET /rest/v1/Chart/usagePieChart?module=portal&commentary=full`

**Purpose**: Water usage breakdown by category

**Data Structure**:
```json
{
  "data": {
    "chartData": {
      "irrigation": {
        "name": "irrigation",
        "value": 59880.835034152,
        ...
      },
      "indoor": {...},
      ...
    }
  }
}
```

**Notes**:
- Categorizes usage (irrigation, indoor, etc.)
- Values in gallons
- Useful for understanding usage patterns

## Download Page

**URL**: `https://paloalto.watersmart.com/index.php/accountPreferences/download`

The download page provides a UI for exporting data. Based on manual inspection:
- **Billing Interval Data**: CSV export available (2017 to present)
- **Hourly Data**: CSV export for recent 3 months
- **Format**: Likely similar to the chart API structures

*Note: Download APIs not yet captured - would require interacting with download forms*

## Data Availability

Based on the captured data:
- **Hourly data**: ~3 months (recent)
- **Daily data**: Several months (weatherConsumptionChart shows back to Aug 2024)
- **Billing period data**: Multiple years (2017+)
- **Annual data**: Multiple years

## Recommended Next Steps

### Phase 2: Test Direct API Calls
1. Extract session cookies from authenticated browser session
2. Test if APIs can be called directly with cookies via `requests` library
3. Document cookie lifetime and refresh requirements

### Phase 3: Implement Download APIs
1. Inspect download page forms
2. Identify POST endpoints for CSV exports
3. Test download parameters (date ranges, formats)

### Phase 4: Design Python API
Similar to electric meter API, create:
```python
class CpauWaterMeter:
    def get_usage(self, start_date, end_date, interval='daily'):
        """
        Retrieve water usage data.

        Args:
            start_date: Start date (date object)
            end_date: End date (date object)
            interval: 'hourly', 'daily', 'monthly', or 'billing'

        Returns:
            List of UsageRecord objects
        """
        pass

    def get_availability_window(self, interval):
        """Find earliest and latest available dates."""
        pass
```

### Phase 5: Handle Challenges
- **Authentication complexity**: SAML flow requires browser automation
- **Session management**: Need to maintain session across API calls
- **Cookie refresh**: Determine if/when re-authentication is needed
- **Rate limiting**: Monitor for any API rate limits

## Files Generated

- `/tmp/watersmart_trackUsage_real.html` - Track Usage page HTML
- `/tmp/watersmart_download_real.html` - Download page HTML
- `/tmp/watersmart_api_calls.json` - Complete API call log with responses
- `/tmp/playwright_run.log` - Full execution log
- `explore_with_playwright.py` - Reusable browser automation script

## Technical Notes

1. **Units**: All water measurements appear to be in gallons
2. **Timestamps**: Unix timestamps (seconds since epoch) for hourly data
3. **Date formats**:
   - ISO format for daily: "YYYY-MM-DD"
   - Compact format for annual: "YYYYMMDD"
4. **Response format**: All APIs return `{\"data\": {...}}` wrapper structure
5. **Browser requirement**: Chromium/Chrome for Playwright automation

## Comparison to Electric Meter

| Feature | Electric Meter | Water Meter |
|---------|---------------|-------------|
| Authentication | Direct JSON POST | SAML/SSO (browser required) |
| API Type | Custom JSON endpoints | RESTful chart APIs |
| Intervals | 15min, hourly, daily, monthly, billing | Hourly, daily, monthly, billing |
| Historical Data | ~10 years | ~3 months (hourly), years (billing) |
| Implementation | Requests library | Playwright + Requests |

## Questions for Further Investigation

1. **Download API parameters**: What parameters does the CSV download accept?
2. **Hourly data window**: Can we request hourly data beyond 3 months?
3. **API parameters**: Do chart APIs accept date range parameters?
4. **Session duration**: How long do watersmart session cookies remain valid?
5. **Direct API access**: Can we bypass SAML after initial auth and reuse cookies?
