# CPAU Test Suite

This directory contains automated tests for the CPAU library and CLI tools.

## Test Organization

```
tests/
├── test_cli_electric.py     # Tests for cpau-electric CLI (✅ 11 tests passing)
├── test_cli_water.py        # Tests for cpau-water CLI (✅ 14 tests passing)
├── test_cli_availability.py # Tests for cpau-availability CLI (✅ 11 tests passing)
├── test_electric_meter.py   # Tests for electric meter API
├── test_water_meter.py      # Tests for water meter API
├── fixtures/                # Mock API response data
│   ├── electric_responses.py
│   └── water_responses.py
├── conftest.py              # Shared pytest fixtures
└── manual/                  # Manual integration tests (require credentials)
    ├── electric/            # Electric meter manual tests
    └── water/               # Water meter manual tests
```

## Running Tests

### Install Test Dependencies

```bash
pip install -e ".[test]"
```

Or for development (includes all dev tools):

```bash
pip install -e ".[dev]"
```

### Run All Automated Tests

```bash
pytest tests/
```

### Run Specific Test Suites

```bash
# CLI tests only (fully passing)
pytest tests/test_cli_electric.py tests/test_cli_water.py -v

# Electric meter tests
pytest tests/test_electric_meter.py -v

# Water meter tests
pytest tests/test_water_meter.py -v
```

### Run Tests with Coverage

```bash
pytest tests/ --cov=cpau --cov-report=html
```

### Run Only Unit Tests (No Integration Tests)

```bash
pytest tests/ -m unit
```

## Test Categories

Tests are marked with pytest markers:

- `@pytest.mark.unit` - Unit tests that don't require external services (fully mocked)
- `@pytest.mark.integration` - Integration tests that may require credentials

## Manual Integration Tests

The `tests/manual/` directory contains integration tests that require actual CPAU credentials and make real API calls. These are excluded from automated test runs.

To run manual tests:

1. Create a `secrets.json` file in the repo root with your CPAU credentials
2. Run specific manual test scripts:

```bash
# Example
python tests/manual/electric/test_data_availability.py
```

## Writing Tests

### CLI Tests

CLI tests should:
- Mock the underlying API calls
- Use temporary files for secrets and output
- Test error handling (missing files, invalid dates, etc.)
- Verify CSV output format

Example:
```python
@patch('cpau.cli.CpauApiSession')
def test_basic_daily_usage(self, mock_session_class, mock_credentials):
    secrets_file = self.create_temp_secrets(mock_credentials)
    # ... test code
```

### API/Meter Tests

API tests should:
- Mock HTTP requests to avoid external dependencies
- Use fixtures from `tests/fixtures/` for mock data
- Test all interval types
- Test error conditions

### Fixtures

Mock API responses are defined in `tests/fixtures/`:
- `electric_responses.py` - Mock responses for electric meter API
- `water_responses.py` - Mock responses for water meter API

## Test Results

Current status:
- ✅ CLI Tests: **36/36 passing**
  - cpau-electric CLI: 11/11 passing
  - cpau-water CLI: 14/14 passing
  - cpau-availability CLI: 11/11 passing
- ⚠️ API Tests: Some tests need mock improvements
  - Integration with actual API calls works (see manual tests)
  - Unit test mocking needs refinement

## Continuous Integration

The automated test suite (excluding manual tests) can be run in CI/CD:

```bash
pytest tests/ --ignore=tests/manual
```

This is configured in `pytest.ini`.
