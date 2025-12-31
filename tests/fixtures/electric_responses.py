"""Mock API responses for electric meter tests."""

import json

# Mock login page HTML with CSRF token
LOGIN_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head><title>CPAU Login</title></head>
<body>
    <form id="form1">
        <input type="hidden" name="__VIEWSTATE" value="mock_viewstate_value" />
        <input type="hidden" name="__EVENTVALIDATION" value="mock_event_validation" />
    </form>
</body>
</html>
"""

# Mock successful login response
LOGIN_SUCCESS_RESPONSE = {
    "d": json.dumps({
        "UserId": "test@example.com",
        "Success": True,
        "Message": "Login successful"
    })
}

# Mock meter information response
METER_INFO_RESPONSE = {
    "d": json.dumps({
        "MeterDetails": [
            {
                "MeterNumber": "12345678",
                "MeterType": "E",
                "MeterAddress": "123 Test St, Palo Alto, CA",
                "MeterStatus": 1,
                "MeterAttribute2": "E-1 Residential"
            }
        ]
    })
}

# Mock daily usage response
DAILY_USAGE_RESPONSE = {
    "d": json.dumps({
        "UsageData": [
            {
                "Date": "12/15/2024",
                "UsageType": "IUsage",
                "Usage": "28.06"
            },
            {
                "Date": "12/15/2024",
                "UsageType": "EUsage",
                "Usage": "0.10"
            },
            {
                "Date": "12/16/2024",
                "UsageType": "IUsage",
                "Usage": "22.25"
            },
            {
                "Date": "12/16/2024",
                "UsageType": "EUsage",
                "Usage": "1.43"
            }
        ]
    })
}

# Mock hourly usage response (single day)
HOURLY_USAGE_RESPONSE = {
    "d": json.dumps({
        "UsageData": [
            {
                "Date": "12/17/2024",
                "Time": "00:00",
                "UsageType": "IUsage",
                "Usage": "0.58"
            },
            {
                "Date": "12/17/2024",
                "Time": "00:00",
                "UsageType": "EUsage",
                "Usage": "0.00"
            },
            {
                "Date": "12/17/2024",
                "Time": "01:00",
                "UsageType": "IUsage",
                "Usage": "0.64"
            },
            {
                "Date": "12/17/2024",
                "Time": "01:00",
                "UsageType": "EUsage",
                "Usage": "0.00"
            }
        ]
    })
}

# Mock 15-minute usage response
FIFTEEN_MIN_USAGE_RESPONSE = {
    "d": json.dumps({
        "UsageData": [
            {
                "Date": "12/17/2024",
                "Time": "00:00",
                "UsageType": "IUsage",
                "Usage": "0.15"
            },
            {
                "Date": "12/17/2024",
                "Time": "00:00",
                "UsageType": "EUsage",
                "Usage": "0.00"
            },
            {
                "Date": "12/17/2024",
                "Time": "00:15",
                "UsageType": "IUsage",
                "Usage": "0.14"
            },
            {
                "Date": "12/17/2024",
                "Time": "00:15",
                "UsageType": "EUsage",
                "Usage": "0.00"
            }
        ]
    })
}

# Mock billing period response
BILLING_USAGE_RESPONSE = {
    "d": json.dumps({
        "UsageData": [
            {
                "BillingPeriod": "11/01/2024 - 11/30/2024",
                "BillingPeriodStart": "11/01/2024",
                "BillingPeriodEnd": "11/30/2024",
                "UsageType": "IUsage",
                "Usage": "689.4"
            },
            {
                "BillingPeriod": "11/01/2024 - 11/30/2024",
                "BillingPeriodStart": "11/01/2024",
                "BillingPeriodEnd": "11/30/2024",
                "UsageType": "EUsage",
                "Usage": "156.2"
            },
            {
                "BillingPeriod": "12/01/2024 - 12/31/2024",
                "BillingPeriodStart": "12/01/2024",
                "BillingPeriodEnd": "12/31/2024",
                "UsageType": "IUsage",
                "Usage": "712.5"
            },
            {
                "BillingPeriod": "12/01/2024 - 12/31/2024",
                "BillingPeriodStart": "12/01/2024",
                "BillingPeriodEnd": "12/31/2024",
                "UsageType": "EUsage",
                "Usage": "168.3"
            }
        ]
    })
}

# Mock empty response (no data)
EMPTY_USAGE_RESPONSE = {
    "d": json.dumps({
        "UsageData": []
    })
}

# Mock error response
ERROR_RESPONSE = {
    "d": json.dumps({
        "Error": "Invalid request",
        "Success": False
    })
}
