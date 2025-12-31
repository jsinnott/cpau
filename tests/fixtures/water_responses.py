"""Mock API responses for water meter tests."""

# Mock hourly water usage response (RealTimeChart API)
HOURLY_USAGE_RESPONSE = {
    "data": {
        "series": [
            {
                "read_datetime": 1702771200,  # 2023-12-17 00:00:00 UTC
                "gallons": 12.5,
                "flags": None,
                "leak_gallons": 0
            },
            {
                "read_datetime": 1702774800,  # 2023-12-17 01:00:00 UTC
                "gallons": 15.3,
                "flags": None,
                "leak_gallons": 0
            },
            {
                "read_datetime": 1702778400,  # 2023-12-17 02:00:00 UTC
                "gallons": 8.7,
                "flags": None,
                "leak_gallons": 0
            }
        ]
    }
}

# Mock daily water usage response (weatherConsumptionChart API)
DAILY_USAGE_RESPONSE = {
    "data": {
        "chartData": {
            "dailyData": {
                "categories": [
                    "2024-12-01",
                    "2024-12-02",
                    "2024-12-03",
                    "2024-12-04",
                    "2024-12-05"
                ],
                "consumption": [
                    168.309,
                    222.169,
                    185.432,
                    201.876,
                    195.543
                ],
                "temperature": [
                    55.5,
                    58.2,
                    60.1,
                    57.8,
                    56.3
                ],
                "precipitation": [
                    0.0,
                    0.0,
                    0.12,
                    0.0,
                    0.0
                ]
            }
        }
    }
}

# Mock billing period response (BillingHistoryChart API)
BILLING_USAGE_RESPONSE = {
    "data": {
        "chart_data": [
            {
                "gallons": "9724.00",
                "period": {
                    "startDate": {
                        "date": "2024-11-01 00:00:00.000000"
                    },
                    "endDate": {
                        "date": "2024-11-30 23:59:59.000000"
                    }
                }
            },
            {
                "gallons": "10156.50",
                "period": {
                    "startDate": {
                        "date": "2024-12-01 00:00:00.000000"
                    },
                    "endDate": {
                        "date": "2024-12-31 23:59:59.000000"
                    }
                }
            }
        ]
    }
}

# Mock monthly usage response (aggregated from daily)
MONTHLY_USAGE_RESPONSE = {
    "data": {
        "chartData": {
            "dailyData": {
                "categories": [
                    "2024-11-01", "2024-11-02", "2024-11-03", "2024-11-04", "2024-11-05",
                    "2024-11-06", "2024-11-07", "2024-11-08", "2024-11-09", "2024-11-10",
                    "2024-11-11", "2024-11-12", "2024-11-13", "2024-11-14", "2024-11-15",
                    "2024-11-16", "2024-11-17", "2024-11-18", "2024-11-19", "2024-11-20",
                    "2024-11-21", "2024-11-22", "2024-11-23", "2024-11-24", "2024-11-25",
                    "2024-11-26", "2024-11-27", "2024-11-28", "2024-11-29", "2024-11-30"
                ],
                "consumption": [
                    150.0, 160.0, 145.0, 155.0, 165.0,
                    170.0, 175.0, 180.0, 160.0, 150.0,
                    155.0, 165.0, 170.0, 175.0, 180.0,
                    185.0, 190.0, 195.0, 200.0, 205.0,
                    210.0, 215.0, 220.0, 225.0, 230.0,
                    235.0, 240.0, 245.0, 250.0, 255.0
                ],
                "temperature": [60.0] * 30,
                "precipitation": [0.0] * 30
            }
        }
    }
}

# Mock empty response
EMPTY_USAGE_RESPONSE = {
    "data": {
        "series": []
    }
}

# Mock availability window response (for testing date ranges)
AVAILABILITY_RESPONSE = {
    "data": {
        "chartData": {
            "dailyData": {
                "categories": ["2017-01-01", "2024-12-31"],
                "consumption": [100.0, 200.0],
                "temperature": [60.0, 60.0],
                "precipitation": [0.0, 0.0]
            }
        }
    }
}
