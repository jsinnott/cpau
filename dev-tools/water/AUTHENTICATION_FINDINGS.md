# Water Meter Authentication Flow Investigation

## Goal
Understand how to authenticate from the CPAU portal to paloalto.watersmart.com to access water meter data.

## Manual Exploration Steps

Since we're encountering Python environment issues, here's how to manually explore the authentication flow using a web browser:

### Step 1: Trace Authentication Flow in Browser

1. **Open browser with Developer Tools**
   - Chrome/Edge: F12 or Right-click → Inspect
   - Go to Network tab
   - Enable "Preserve log" to capture redirects

2. **Login to CPAU Portal**
   - Navigate to: https://mycpau.cityofpaloalto.org/Portal
   - Login with your credentials
   - Observe the login request in Network tab

3. **Navigate to Water Usage**
   - Look for links to water usage in the portal
   - Possible URLs to try:
     - Direct: https://paloalto.watersmart.com
     - Track Usage: https://paloalto.watersmart.com/index.php/trackUsage
     - Download: https://paloalto.watersmart.com/index.php/accountPreferences/download

4. **Capture the Redirect Chain**
   - Watch Network tab for:
     - Redirects (301, 302, 307, 308 responses)
     - SAML requests/responses
     - Authentication tokens
     - Session cookies being set

### Step 2: Document Findings

Record the following:

#### A. Initial Navigation
- [ ] Starting URL clicked in CPAU portal
- [ ] First redirect URL
- [ ] Any SAML/SSO endpoints involved

#### B. Authentication Exchange
- [ ] SAML Request parameters (if any)
- [ ] SAML Response parameters (if any)
- [ ] Any relay state or session tokens
- [ ] Final landing page URL

#### C. Session State
- [ ] Cookies set for `.watersmart.com` domain
- [ ] Cookies set for `paloalto.watersmart.com`
- [ ] Any authorization headers
- [ ] Session identifiers

#### D. API Endpoints
Once authenticated, inspect the Track Usage page:
- [ ] XHR/Fetch requests for chart data
- [ ] Request URLs
- [ ] Request parameters (date ranges, etc.)
- [ ] Response formats (JSON, CSV, etc.)

Inspect the Download page:
- [ ] Download URLs for billing data
- [ ] Download URLs for hourly data
- [ ] Request parameters
- [ ] Response formats

## Key Questions to Answer

1. **Can we navigate directly to watersmart.com after CPAU login?**
   - Does the CPAU session automatically work for watersmart?
   - Or do we need to follow a specific redirect flow?

2. **Is SAML/SSO being used?**
   - Look for SAMLRequest/SAMLResponse in redirect URLs
   - Check for authentication assertions

3. **What cookies are required?**
   - Which cookies need to be shared between domains?
   - Are there specific watersmart session cookies?

4. **Can we programmatically access the APIs?**
   - Do the data APIs require additional authentication?
   - Or do they work with the session cookies alone?

## Next Steps

Once manual exploration is complete, document findings here and then:

1. Create Python script to replicate the authentication flow
2. Test programmatic access to watersmart APIs
3. Design CpauWaterMeter class based on discovered APIs

## Environment Note

The current Python environment in this project has dependency issues. Consider:
- Installing dependencies properly: `pip install requests`
- Or using a different Python environment for development
- Or running scripts from outside the virtualenv
