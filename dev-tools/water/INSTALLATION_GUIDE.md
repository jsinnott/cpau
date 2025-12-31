# Water Meter Installation Guide

## Overview

The CPAU water meter API requires **additional dependencies** compared to the electric meter API due to the SAML/SSO authentication used by watersmart.com.

## Quick Start

```bash
# Install the package
pip install cpau

# Install Playwright browser (ONE-TIME SETUP)
playwright install chromium
```

That's it! The extra step is downloading the Chromium browser (~100MB) that Playwright uses for authentication.

## Why the Extra Step?

| Feature | Electric Meter | Water Meter |
|---------|---------------|-------------|
| Authentication | Simple JSON POST | SAML/SSO (requires browser) |
| Dependencies | `requests` only | `requests` + `playwright` |
| Install steps | 1 step | 2 steps |
| Disk space | Minimal | +100MB (Chromium) |

The water meter data is hosted on a third-party site (paloalto.watersmart.com) that uses SAML authentication, which requires JavaScript execution - thus the need for a headless browser.

## Detailed Installation

### Step 1: Install the Package

```bash
pip install cpau
```

This installs:
- Core `cpau` library
- `requests` library (for API calls)
- `playwright` library (for browser automation)
- All other dependencies

### Step 2: Download Chromium Browser

```bash
playwright install chromium
```

This downloads a headless Chromium browser (~100MB) that Playwright uses for authentication.

**Important Notes**:
- This is a **ONE-TIME** installation step
- The browser is stored in your system's cache directory
- Only needs to be re-run if you delete the browser cache
- You can use `playwright install --help` for options

### Step 3: Verify Installation

```python
from cpau import CpauWaterMeter

# If this works without errors, you're all set!
meter = CpauWaterMeter(username='your_username', password='your_password')
```

## Platform-Specific Notes

### Linux

On Linux, you may need additional system dependencies for Chromium:

```bash
# Ubuntu/Debian
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2

# Or use Playwright's helper:
playwright install-deps chromium
```

### macOS

No additional system dependencies needed. The Chromium download just works.

### Windows

No additional system dependencies needed. The Chromium download just works.

## CI/CD Integration

### GitHub Actions

```yaml
- name: Install dependencies
  run: |
    pip install cpau
    playwright install chromium
    playwright install-deps  # Linux only
```

### Docker

```dockerfile
FROM python:3.9

# Install Python package
RUN pip install cpau

# Install Playwright and browser
RUN playwright install chromium
RUN playwright install-deps chromium

# Your application code
COPY . /app
WORKDIR /app
```

## Disk Space Requirements

| Component | Size | Purpose |
|-----------|------|---------|
| `cpau` package | ~50 KB | Core library |
| `playwright` package | ~2 MB | Browser automation |
| Chromium browser | ~100 MB | Headless browser for auth |
| **Total** | **~102 MB** | |

## Headless vs. Visible Browser

By default, the water meter API uses **headless mode** - no browser window is visible:

```python
# Headless (default) - no visible browser window
meter = CpauWaterMeter(username, password)

# Visible browser (for debugging)
meter = CpauWaterMeter(username, password, headless=False)
```

**When to use visible browser**:
- Debugging authentication issues
- Understanding the SAML flow
- Development and testing

**Production use**: Always use headless mode (default).

## Performance Impact

### First API Call (includes authentication)
```
Electric meter: <1 second
Water meter:   ~15 seconds (Playwright authentication)
```

### Subsequent API Calls (reuses session)
```
Electric meter: <1 second
Water meter:   <1 second (no re-authentication needed)
```

**Example**:
```python
meter = CpauWaterMeter(username, password)

# First call: ~15s (includes auth)
hourly = meter.get_usage(start, end, interval='hourly')

# Second call: <1s (reuses session)
daily = meter.get_usage(start, end, interval='daily')

# Third call: <1s (reuses session)
billing = meter.get_usage(start, end, interval='billing')
```

The authentication cost is amortized across multiple API calls.

## Troubleshooting

### Error: `playwright` command not found

**Problem**: Playwright CLI not in PATH

**Solution**:
```bash
# Try with python -m
python -m playwright install chromium
```

### Error: Browser executable doesn't exist

**Problem**: Chromium not downloaded

**Solution**:
```bash
playwright install chromium
```

### Error: Failed to launch browser

**Problem**: Missing system dependencies (Linux)

**Solution**:
```bash
playwright install-deps chromium
```

### Error: Authentication failed

**Problem**: Wrong credentials or CPAU portal down

**Solution**:
1. Verify credentials work at https://mycpau.cityofpaloalto.org/Portal
2. Try with `headless=False` to see what's happening
3. Check CPAU portal is accessible

## Security Considerations

### Headless Browser

The headless Chromium browser:
- ✓ Runs in sandboxed environment
- ✓ Only used for authentication
- ✓ Closes immediately after auth
- ✓ Does not store any data between runs

### Credentials

Never hardcode credentials:

```python
# ✗ BAD - credentials in code
meter = CpauWaterMeter('myuser', 'mypass')

# ✓ GOOD - credentials from environment
import os
meter = CpauWaterMeter(
    os.getenv('CPAU_USERNAME'),
    os.getenv('CPAU_PASSWORD')
)

# ✓ GOOD - credentials from config file
import json
with open('secrets.json') as f:
    creds = json.load(f)
meter = CpauWaterMeter(creds['username'], creds['password'])
```

## Comparison with Electric Meter

### Installation

**Electric Meter**:
```bash
pip install cpau  # Done!
```

**Water Meter**:
```bash
pip install cpau
playwright install chromium  # Extra step
```

### Usage

Both have identical APIs (once installed):

```python
# Electric meter
from cpau import CpauElectricMeter
meter = CpauElectricMeter(username, password)
usage = meter.get_usage(start, end, interval='hourly')

# Water meter
from cpau import CpauWaterMeter
meter = CpauWaterMeter(username, password)
usage = meter.get_usage(start, end, interval='hourly')
```

## FAQ

**Q: Do I need to install Chromium every time?**
A: No, just once. Playwright caches the browser.

**Q: Will a browser window pop up?**
A: No (by default). The browser runs in headless mode.

**Q: Can I use my existing Chrome browser?**
A: No, Playwright uses its own Chromium build for consistency.

**Q: How much slower is water meter vs electric?**
A: ~15 seconds slower for first call (authentication), then same speed.

**Q: Can I avoid the Playwright dependency?**
A: No, SAML authentication requires browser automation. But you only need to install it once.

**Q: Does this work in Docker/serverless?**
A: Yes! Just include the Playwright install steps in your Dockerfile or deployment script.

**Q: Can I use Firefox or Safari instead of Chromium?**
A: Chromium is recommended and tested. Firefox might work (`playwright install firefox`).

## Support

If you encounter issues:

1. Check this guide's troubleshooting section
2. Verify installation: `playwright --version`
3. Test with `headless=False` to see browser
4. Open an issue on GitHub with error details

## Summary

**For electric meter only**: One command
```bash
pip install cpau
```

**For water meter support**: Two commands
```bash
pip install cpau
playwright install chromium
```

The extra step downloads a headless browser (~100MB) needed for SAML authentication. It's a one-time setup and works seamlessly after that!
