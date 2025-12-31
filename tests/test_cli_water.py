"""Tests for cpau-water CLI."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import date, datetime
from io import StringIO

from cpau.cli import CpauWaterCli
from cpau.meter import UsageRecord


@pytest.mark.unit
class TestCpauWaterCli:
    """Tests for cpau-water command-line interface."""

    def create_temp_secrets(self, credentials):
        """Create a temporary secrets file."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(credentials, temp_file)
        temp_file.close()
        return temp_file.name

    def create_mock_water_records(self, num_records=3):
        """Create mock water usage records for testing."""
        records = []
        for i in range(num_records):
            record = UsageRecord(
                date=datetime(2024, 12, i+1),
                import_kwh=150.0 + (i * 10),  # Gallons in import_kwh field
                export_kwh=0.0,
                net_kwh=150.0 + (i * 10),
                billing_period_start=None,
                billing_period_end=None,
                billing_period_length=None
            )
            records.append(record)
        return records

    @patch('cpau.cli.CpauWaterMeter')
    def test_basic_daily_usage(self, mock_meter_class, mock_credentials):
        """Test basic daily water usage retrieval."""
        # Create temp secrets file
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock meter
            mock_meter = MagicMock()
            mock_meter.get_usage.return_value = self.create_mock_water_records()
            mock_meter_class.return_value = mock_meter

            # Run CLI
            cli = CpauWaterCli()
            with patch('sys.stdout', new=StringIO()) as fake_out:
                exit_code = cli.go([
                    '--interval', 'daily',
                    '--secrets-file', secrets_file,
                    '2024-12-01',
                    '2024-12-03'
                ])

                # Check exit code
                assert exit_code == 0

                # Check that meter.get_usage was called
                mock_meter.get_usage.assert_called_once_with(
                    interval='daily',
                    start_date=date(2024, 12, 1),
                    end_date=date(2024, 12, 3)
                )

                # Check CSV output
                output = fake_out.getvalue()
                assert 'date,gallons' in output
                assert '2024-12-01' in output
                assert '150.0' in output  # First record's gallons

        finally:
            # Clean up temp file
            Path(secrets_file).unlink()

    @patch('cpau.cli.CpauWaterMeter')
    def test_hourly_usage(self, mock_meter_class, mock_credentials):
        """Test hourly water usage retrieval."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock meter
            mock_meter = MagicMock()

            # Create hourly records with datetime
            hourly_records = [
                UsageRecord(
                    date=datetime(2024, 12, 1, i, 0),
                    import_kwh=12.5 + i,  # Gallons
                    export_kwh=0.0,
                    net_kwh=12.5 + i,
                    billing_period_start=None,
                    billing_period_end=None,
                    billing_period_length=None
                )
                for i in range(3)
            ]
            mock_meter.get_usage.return_value = hourly_records
            mock_meter_class.return_value = mock_meter

            # Run CLI
            cli = CpauWaterCli()
            with patch('sys.stdout', new=StringIO()) as fake_out:
                exit_code = cli.go([
                    '--interval', 'hourly',
                    '--secrets-file', secrets_file,
                    '2024-12-01'
                ])

                assert exit_code == 0

                # Check that ISO format is used for hourly
                output = fake_out.getvalue()
                assert '2024-12-01T00:00:00' in output or '2024-12-01 00:00:00' in output

        finally:
            Path(secrets_file).unlink()

    @patch('cpau.cli.CpauWaterMeter')
    def test_billing_interval(self, mock_meter_class, mock_credentials):
        """Test billing interval with extended fieldnames."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock meter
            mock_meter = MagicMock()

            # Create billing records
            billing_records = [
                UsageRecord(
                    date=datetime(2024, 12, 1),
                    import_kwh=9724.0,  # Gallons
                    export_kwh=0.0,
                    net_kwh=9724.0,
                    billing_period_start=date(2024, 12, 1),
                    billing_period_end=date(2024, 12, 31),
                    billing_period_length=31
                )
            ]
            mock_meter.get_usage.return_value = billing_records
            mock_meter_class.return_value = mock_meter

            # Run CLI
            cli = CpauWaterCli()
            with patch('sys.stdout', new=StringIO()) as fake_out:
                exit_code = cli.go([
                    '--interval', 'billing',
                    '--secrets-file', secrets_file,
                    '2024-12-01'
                ])

                assert exit_code == 0

                # Check billing-specific fields in output
                output = fake_out.getvalue()
                assert 'billing_period_start' in output
                assert 'billing_period_end' in output
                assert 'billing_period_length' in output
                assert '9724.0' in output

        finally:
            Path(secrets_file).unlink()

    @patch('cpau.cli.CpauWaterMeter')
    def test_monthly_usage(self, mock_meter_class, mock_credentials):
        """Test monthly aggregated water usage."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock meter
            mock_meter = MagicMock()

            # Create monthly record
            monthly_records = [
                UsageRecord(
                    date=datetime(2024, 12, 1),
                    import_kwh=5625.0,  # Monthly total in gallons
                    export_kwh=0.0,
                    net_kwh=5625.0,
                    billing_period_start=None,
                    billing_period_end=None,
                    billing_period_length=None
                )
            ]
            mock_meter.get_usage.return_value = monthly_records
            mock_meter_class.return_value = mock_meter

            # Run CLI
            cli = CpauWaterCli()
            with patch('sys.stdout', new=StringIO()) as fake_out:
                exit_code = cli.go([
                    '--interval', 'monthly',
                    '--secrets-file', secrets_file,
                    '2024-12-01'
                ])

                assert exit_code == 0

                # Check output
                output = fake_out.getvalue()
                assert '5625.0' in output

        finally:
            Path(secrets_file).unlink()

    @patch('cpau.cli.CpauWaterMeter')
    def test_output_to_file(self, mock_meter_class, mock_credentials):
        """Test writing output to file."""
        secrets_file = self.create_temp_secrets(mock_credentials)
        output_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        output_file.close()

        try:
            # Mock meter
            mock_meter = MagicMock()
            mock_meter.get_usage.return_value = self.create_mock_water_records()
            mock_meter_class.return_value = mock_meter

            # Run CLI
            cli = CpauWaterCli()
            exit_code = cli.go([
                '--interval', 'daily',
                '--secrets-file', secrets_file,
                '--output-file', output_file.name,
                '2024-12-01',
                '2024-12-03'
            ])

            assert exit_code == 0

            # Verify output file was created and has content
            output_path = Path(output_file.name)
            assert output_path.exists()
            content = output_path.read_text()
            assert 'date,gallons' in content
            assert '2024-12-01' in content or '150.0' in content

        finally:
            Path(secrets_file).unlink()
            Path(output_file.name).unlink()

    @patch('cpau.cli.CpauWaterMeter')
    def test_custom_cache_dir(self, mock_meter_class, mock_credentials):
        """Test using custom cache directory."""
        secrets_file = self.create_temp_secrets(mock_credentials)
        cache_dir = tempfile.mkdtemp()

        try:
            # Mock meter
            mock_meter = MagicMock()
            mock_meter.get_usage.return_value = self.create_mock_water_records()
            mock_meter_class.return_value = mock_meter

            # Run CLI with custom cache dir
            cli = CpauWaterCli()
            with patch('sys.stdout', new=StringIO()):
                exit_code = cli.go([
                    '--interval', 'daily',
                    '--secrets-file', secrets_file,
                    '--cache-dir', cache_dir,
                    '2024-12-01'
                ])

                assert exit_code == 0

                # Verify CpauWaterMeter was called with custom cache_dir
                mock_meter_class.assert_called_once()
                call_kwargs = mock_meter_class.call_args[1]
                assert call_kwargs['cache_dir'] == cache_dir

        finally:
            Path(secrets_file).unlink()
            Path(cache_dir).rmdir()

    def test_missing_secrets_file(self):
        """Test error handling when secrets file is missing."""
        cli = CpauWaterCli()

        exit_code = cli.go([
            '--secrets-file', '/nonexistent/secrets.json',
            '2024-12-01'
        ])

        assert exit_code == 1

    def test_invalid_date_format(self, mock_credentials):
        """Test error handling for invalid date format."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            cli = CpauWaterCli()
            exit_code = cli.go([
                '--secrets-file', secrets_file,
                '12/01/2024'  # Wrong format
            ])

            assert exit_code == 1

        finally:
            Path(secrets_file).unlink()

    def test_invalid_secrets_json(self):
        """Test error handling for invalid JSON in secrets file."""
        # Create temp file with invalid JSON
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        temp_file.write("{ invalid json")
        temp_file.close()

        try:
            cli = CpauWaterCli()
            exit_code = cli.go([
                '--secrets-file', temp_file.name,
                '2024-12-01'
            ])

            assert exit_code == 1

        finally:
            Path(temp_file.name).unlink()

    def test_missing_credentials_fields(self):
        """Test error handling when secrets file is missing required fields."""
        # Create secrets file without password
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump({"userid": "test@example.com"}, temp_file)
        temp_file.close()

        try:
            cli = CpauWaterCli()
            exit_code = cli.go([
                '--secrets-file', temp_file.name,
                '2024-12-01'
            ])

            assert exit_code == 1

        finally:
            Path(temp_file.name).unlink()

    @patch('cpau.cli.CpauWaterMeter')
    def test_water_meter_error_handling(self, mock_meter_class, mock_credentials):
        """Test error handling when water meter API call fails."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock meter that raises error
            mock_meter_class.side_effect = Exception("Connection failed")

            cli = CpauWaterCli()
            exit_code = cli.go([
                '--secrets-file', secrets_file,
                '2024-12-01'
            ])

            assert exit_code == 1

        finally:
            Path(secrets_file).unlink()

    @patch('cpau.cli.CpauWaterMeter')
    def test_verbose_flag(self, mock_meter_class, mock_credentials):
        """Test verbose logging flag."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock meter
            mock_meter = MagicMock()
            mock_meter.get_usage.return_value = self.create_mock_water_records()
            mock_meter_class.return_value = mock_meter

            # Run CLI with verbose flag
            cli = CpauWaterCli()
            with patch('sys.stdout', new=StringIO()):
                exit_code = cli.go([
                    '--verbose',
                    '--interval', 'daily',
                    '--secrets-file', secrets_file,
                    '2024-12-01'
                ])

                assert exit_code == 0

        finally:
            Path(secrets_file).unlink()

    @patch('cpau.cli.CpauWaterMeter')
    def test_default_end_date(self, mock_meter_class, mock_credentials):
        """Test that end_date defaults to today when not provided."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock meter
            mock_meter = MagicMock()
            mock_meter.get_usage.return_value = []
            mock_meter_class.return_value = mock_meter

            # Run CLI without end_date
            cli = CpauWaterCli()
            with patch('sys.stdout', new=StringIO()):
                exit_code = cli.go([
                    '--secrets-file', secrets_file,
                    '2024-12-01'  # No end_date
                ])

                assert exit_code == 0

                # Verify get_usage was called with a default end_date
                assert mock_meter.get_usage.called
                call_args = mock_meter.get_usage.call_args
                # end_date should be set to today
                assert call_args[1]['end_date'] is not None

        finally:
            Path(secrets_file).unlink()

    @patch('cpau.cli.CpauWaterMeter')
    def test_silent_flag(self, mock_meter_class, mock_credentials):
        """Test silent flag suppresses log output."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock meter
            mock_meter = MagicMock()
            mock_meter.get_usage.return_value = self.create_mock_water_records()
            mock_meter_class.return_value = mock_meter

            # Run CLI with silent flag
            cli = CpauWaterCli()
            with patch('sys.stdout', new=StringIO()):
                exit_code = cli.go([
                    '--silent',
                    '--interval', 'daily',
                    '--secrets-file', secrets_file,
                    '2024-12-01'
                ])

                assert exit_code == 0

        finally:
            Path(secrets_file).unlink()
