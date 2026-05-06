"""Mock API responses for electric meter tests.

The shapes here mirror what the CPAU portal actually returns: the response
JSON has a single string-typed top-level key 'd' which decodes to the real
payload. _make_api_request unwraps 'd' before returning, so meter tests
that mock _make_api_request directly assign the unwrapped payload.

Field names match what session.py and electric_meter.py parse:

  Login response payload:
    Either {'STATUS': '1', ...} or {'UserID': ..., ...} signals success.

  Meter info payload:
    {'MeterDetails': [{'MeterNumber', 'MeterType', 'Status', 'Address',
                       'MeterAttribute2'}, ...]}.

  Usage payload (LoadUsage endpoint):
    {'objUsageGenerationResultSetTwo': [{...}, ...]}.
    For daily/hourly/15min: each record has 'UsageDate' (MM/DD/YY),
    'UsageType' ('IUsage' or 'Eusage'), 'UsageValue', and (for hourly/
    15min) 'Hourly' (HH:MM).
    For billing: each record has 'Year', 'Month', 'BillPeriod'
    (MM/DD/YY to MM/DD/YY), 'UsageType', 'UsageValue'.
"""

import json


# HTML returned by the homepage and the Usages page. The two pages use
# different CSRF inputs, so this fixture carries both names so the same
# string can stand in for either page in tests:
#   - "__RequestVerificationToken" is the homepage form's token
#   - "ctl00$hdnCSRFToken" is the per-page token used by Usages.aspx
LOGIN_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head><title>CPAU Login</title></head>
<body>
    <form id="form1">
        <input type="hidden" name="__RequestVerificationToken" value="mock_csrf_token" />
        <input type="hidden" name="ctl00$hdnCSRFToken" value="mock_page_csrf_token" />
    </form>
</body>
</html>
"""

LOGIN_SUCCESS_RESPONSE = {
    "d": json.dumps({
        "STATUS": "1",
        "UserID": "test@example.com",
        "Message": "Login successful"
    })
}

METER_INFO_RESPONSE = {
    "d": json.dumps({
        "MeterDetails": [
            {
                "MeterNumber": "12345678",
                "MeterType": "E",
                "Address": "123 Test St, Palo Alto, CA",
                "Status": 1,
                "MeterAttribute2": "E-1 Residential"
            }
        ]
    })
}

DAILY_USAGE_RESPONSE = {
    "d": json.dumps({
        "objUsageGenerationResultSetTwo": [
            {"UsageDate": "12/15/24", "UsageType": "IUsage", "UsageValue": 28.06},
            {"UsageDate": "12/15/24", "UsageType": "Eusage", "UsageValue": 0.10},
            {"UsageDate": "12/16/24", "UsageType": "IUsage", "UsageValue": 22.25},
            {"UsageDate": "12/16/24", "UsageType": "Eusage", "UsageValue": 1.43},
        ]
    })
}

HOURLY_USAGE_RESPONSE = {
    "d": json.dumps({
        "objUsageGenerationResultSetTwo": [
            {"UsageDate": "12/17/24", "Hourly": "00:00", "UsageType": "IUsage", "UsageValue": 0.58},
            {"UsageDate": "12/17/24", "Hourly": "00:00", "UsageType": "Eusage", "UsageValue": 0.00},
            {"UsageDate": "12/17/24", "Hourly": "01:00", "UsageType": "IUsage", "UsageValue": 0.64},
            {"UsageDate": "12/17/24", "Hourly": "01:00", "UsageType": "Eusage", "UsageValue": 0.00},
        ]
    })
}

FIFTEEN_MIN_USAGE_RESPONSE = {
    "d": json.dumps({
        "objUsageGenerationResultSetTwo": [
            {"UsageDate": "12/17/24", "Hourly": "00:00", "UsageType": "IUsage", "UsageValue": 0.15},
            {"UsageDate": "12/17/24", "Hourly": "00:00", "UsageType": "Eusage", "UsageValue": 0.00},
            {"UsageDate": "12/17/24", "Hourly": "00:15", "UsageType": "IUsage", "UsageValue": 0.14},
            {"UsageDate": "12/17/24", "Hourly": "00:15", "UsageType": "Eusage", "UsageValue": 0.00},
        ]
    })
}

BILLING_USAGE_RESPONSE = {
    "d": json.dumps({
        "objUsageGenerationResultSetTwo": [
            {
                "Year": 2024, "Month": 11,
                "BillPeriod": "11/01/24 to 11/30/24",
                "UsageType": "IUsage", "UsageValue": 689.4,
            },
            {
                "Year": 2024, "Month": 11,
                "BillPeriod": "11/01/24 to 11/30/24",
                "UsageType": "Eusage", "UsageValue": 156.2,
            },
            {
                "Year": 2024, "Month": 12,
                "BillPeriod": "12/01/24 to 12/31/24",
                "UsageType": "IUsage", "UsageValue": 712.5,
            },
            {
                "Year": 2024, "Month": 12,
                "BillPeriod": "12/01/24 to 12/31/24",
                "UsageType": "Eusage", "UsageValue": 168.3,
            },
        ]
    })
}

EMPTY_USAGE_RESPONSE = {
    "d": json.dumps({
        "objUsageGenerationResultSetTwo": []
    })
}

# Real-world variant: as of mid-2025 the LoadUsage endpoint returns billing
# records with an empty BillPeriod field and instead populates separate
# FromDate / ToDate fields. The parser must fall back to those when
# BillPeriod is empty.
BILLING_USAGE_RESPONSE_FROM_DATE = {
    "d": json.dumps({
        "objUsageGenerationResultSetTwo": [
            {
                "Year": 2025, "Month": 11,
                "BillPeriod": "",
                "FromDate": "11/01/25", "ToDate": "11/30/25",
                "UsageType": "IUsage", "UsageValue": 689.4,
            },
            {
                "Year": 2025, "Month": 11,
                "BillPeriod": "",
                "FromDate": "11/01/25", "ToDate": "11/30/25",
                "UsageType": "Eusage", "UsageValue": 156.2,
            },
            {
                "Year": 2025, "Month": 12,
                "BillPeriod": "",
                "FromDate": "12/01/25", "ToDate": "12/31/25",
                "UsageType": "IUsage", "UsageValue": 712.5,
            },
            {
                "Year": 2025, "Month": 12,
                "BillPeriod": "",
                "FromDate": "12/01/25", "ToDate": "12/31/25",
                "UsageType": "Eusage", "UsageValue": 168.3,
            },
        ]
    })
}
