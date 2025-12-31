# Phase 2 Findings: Cookie-Based API Access

## Summary

Successfully validated the hybrid approach: **Playwright for authentication + requests library for API calls**.

## Test Results

### Test 1: Direct API Access with Extracted Cookies ✓

**Script**: `test_cookies_with_requests.py`

**Results**:
- All 6 water data APIs accessible via `requests` library
- Authentication via Playwright headless mode (17 seconds)
- 12,136 hourly data points retrieved successfully

**APIs Tested**:
1. ✓ RealTimeChart - 12,136 data points
2. ✓ weatherConsumptionChart - Chart data
3. ✓ BillingHistoryChart - Historical periods
4. ✓ yearOverYearChart - Monthly comparison
5. ✓ annualChart - Yearly totals
6. ✓ usagePieChart - Category breakdown

**Conclusion**: Cookies extracted from Playwright work perfectly with `requests` library.

### Test 2: Cookie Lifetime Analysis ✓

**Script**: `test_cookie_lifetime.py`

**Results**:
- Cookies valid for **at least 10 minutes** (tested up to 602 seconds)
- Likely valid much longer (all tests passed)
- Session cookies have no explicit expiration time

**Cookie Analysis**:

| Cookie | Type | Expires | Purpose |
|--------|------|---------|---------|
| PHPSESSID | Session | Browser close | Main session identifier |
| SimpleSAMLSessionID | Session | Browser close | SAML session |
| SimpleSAMLAuthToken | Session | Browser close | SAML authentication token |
| _ga | Persistent | ~400 days | Google Analytics (not auth) |
| _ga_R4227GS71J | Persistent | ~400 days | Google Analytics (not auth) |

**Important Finding**: Session cookies are marked to expire on "browser close", but since we're saving and reusing them, they remain valid as long as the server-side session is active.

**Timeline**:
- ✓ 0 seconds: Valid
- ✓ 60 seconds (1 min): Valid
- ✓ 301 seconds (5 min): Valid
- ✓ 602 seconds (10 min): Valid
- Unknown: Actual expiration time (likely hours or days)

## Hybrid Approach Architecture

### Recommended Implementation

```python
class WatersessionCookieManager:
    """Manages watersmart.com session cookies."""

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.cookies = None
        self.authenticated_at = None

    def authenticate(self):
        """Authenticate using Playwright and extract cookies."""
        # Use Playwright headless
        # Extract and store cookies
        # Record authentication timestamp

    def is_authenticated(self):
        """Check if we have valid cookies."""
        return self.cookies is not None

    def needs_refresh(self):
        """Determine if re-authentication is needed."""
        # Strategy: Re-auth if API returns 401
        # Or: Proactive refresh after threshold (e.g., 1 hour)

    def get_session(self):
        """Get requests.Session with current cookies."""
        if not self.is_authenticated() or self.needs_refresh():
            self.authenticate()

        session = requests.Session()
        for cookie in self.cookies:
            session.cookies.set(cookie['name'], cookie['value'])
        return session
```

### Usage Pattern

```python
# Initialize once
cookie_mgr = WatersessionCookieManager(username, password)

# Use for multiple API calls
session = cookie_mgr.get_session()
data1 = session.get(api_url_1).json()
data2 = session.get(api_url_2).json()

# Automatic re-authentication on 401
# or when threshold exceeded
```

## Re-Authentication Strategy

### Option 1: Reactive (Recommended)
- Catch 401 (Unauthorized) responses
- Re-authenticate automatically
- Retry failed request
- **Pros**: Simple, only authenticates when needed
- **Cons**: One failed request before recovery

### Option 2: Proactive
- Re-authenticate after time threshold (e.g., 1 hour)
- Never let cookies expire
- **Pros**: No failed requests
- **Cons**: May re-auth unnecessarily, adds complexity

### Option 3: Hybrid
- Use reactive as primary strategy
- Add proactive threshold for long-running applications
- **Pros**: Best of both worlds
- **Cons**: More complex

**Recommendation**: Start with **Reactive** (Option 1) - it's simpler and sufficient for most use cases.

## Performance Considerations

### Authentication Cost
- Playwright headless: ~17 seconds
- Happens once per session
- Amortized over many API calls

### API Call Performance
After authentication:
- API calls use `requests` library (fast)
- No browser overhead
- Multiple calls reuse same cookies

### Example Timeline
```
Time  | Action
------|-------
0:00  | authenticate() - 17s (Playwright)
0:17  | get_usage('hourly') - 0.5s (requests)
0:18  | get_usage('daily') - 0.4s (requests)
0:19  | get_usage('billing') - 0.3s (requests)
------|-------
Total: 18.2s for 3 different datasets
```

Compared to authenticating each time:
```
Time  | Action
------|-------
0:00  | authenticate() + get_usage('hourly') - 17.5s
0:17  | authenticate() + get_usage('daily') - 17.4s
0:35  | authenticate() + get_usage('billing') - 17.3s
------|-------
Total: 52.2s for same 3 datasets
```

**Cookie reuse saves 34 seconds (66% faster) for this example.**

## Implementation Roadmap

### Phase 3: API Design
- [ ] Design `CpauWaterMeter` class interface
- [ ] Match `CpauElectricMeter` API where possible
- [ ] Define data models (gallons vs kWh, etc.)
- [ ] Design error handling

### Phase 4: Core Implementation
- [ ] Implement `WatersessionCookieManager`
- [ ] Implement `CpauWaterMeter` class
- [ ] Parse API responses into `UsageRecord` objects
- [ ] Implement date range handling
- [ ] Add availability window detection

### Phase 5: Integration & Testing
- [ ] Add to main package structure
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Update CLI to support water meter
- [ ] Update documentation

## Dependencies

### New Dependencies for Water Meter
```
playwright==1.57.0  # Already in requirements.txt
```

### Installation Steps
Users will need to run:
```bash
pip install cpau
playwright install chromium  # Downloads ~100MB browser
```

**Important**: Document this extra step in README!

## Comparison: Electric vs Water

| Feature | Electric Meter | Water Meter |
|---------|---------------|-------------|
| Auth method | JSON POST | SAML/SSO (Playwright) |
| Auth time | <1 second | ~17 seconds |
| Session cookies | Simple | Complex (SAML) |
| Cookie lifetime | Unknown | 10+ minutes (likely hours) |
| API calls | requests | requests (after auth) |
| Browser needed | No | Yes (headless) |
| Extra install | No | `playwright install chromium` |

## Next Steps

1. **Create cookie manager class** - Implement session management
2. **Design CpauWaterMeter API** - Match electric meter interface
3. **Document Playwright requirement** - Update README with install steps
4. **Consider caching** - Save cookies to disk to persist across runs?

## Open Questions

1. **Actual cookie expiration**: How long do cookies really last?
   - Current data: Valid for 10+ minutes
   - Need: Test over hours/days to find true limit
   - Impact: Determines if we need aggressive re-auth or not

2. **Cookie persistence**: Should we cache cookies to disk?
   - Pro: Avoid re-auth on every program run
   - Con: Security concern (cookies in plaintext)
   - Decision: Start without caching, add if needed

3. **Multiple accounts**: How to handle users with multiple CPAU accounts?
   - Need: Separate cookie storage per account
   - Solution: Key cookies by username or account number

4. **Concurrent access**: Thread-safe cookie management?
   - Probably not needed for typical use case
   - Can add threading.Lock if required later
