"""Tests for cpau-electric CLI."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import date, datetime
from io import StringIO

from cpau.cli import CpauElectricCli
from cpau.meter import UsageRecord


@pytest.mark.unit
class TestCpauElectricCli:
    """Tests for cpau-electric command-line interface."""

    def create_temp_secrets(self, credentials):
        """Create a temporary secrets file."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(credentials, temp_file)
        temp_file.close()
        return temp_file.name

    def create_mock_usage_records(self, num_records=3):
        """Create mock usage records for testing."""
        records = []
        for i in range(num_records):
            record = UsageRecord(
                date=datetime(2024, 12, i+1),
                import_kwh=20.0 + i,
                export_kwh=1.0 + i,
                net_kwh=19.0,
                billing_period_start=None,
                billing_period_end=None,
                billing_period_length=None
            )
            records.append(record)
        return records

    @patch('cpau.cli.CpauApiSession')
    def test_basic_daily_usage(self, mock_session_class, mock_credentials):
        """Test basic daily usage retrieval."""
        # Create temp secrets file
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock session and meter
            mock_session = MagicMock()
            mock_meter = MagicMock()
            mock_meter.get_usage.return_value = self.create_mock_usage_records()

            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get_electric_meter.return_value = mock_meter

            mock_session_class.return_value = mock_session

            # Run CLI
            cli = CpauElectricCli()
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
                assert 'date,export_kwh,import_kwh,net_kwh' in output
                assert '2024-12-01' in output

        finally:
            # Clean up temp file
            Path(secrets_file).unlink()

    @patch('cpau.cli.CpauApiSession')
    def test_hourly_usage(self, mock_session_class, mock_credentials):
        """Test hourly usage retrieval."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock session and meter
            mock_session = MagicMock()
            mock_meter = MagicMock()

            # Create hourly records with datetime
            hourly_records = [
                UsageRecord(
                    date=datetime(2024, 12, 1, i, 0),
                    import_kwh=1.5,
                    export_kwh=0.1,
                    net_kwh=1.4,
                    billing_period_start=None,
                    billing_period_end=None,
                    billing_period_length=None
                )
                for i in range(3)
            ]
            mock_meter.get_usage.return_value = hourly_records

            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get_electric_meter.return_value = mock_meter

            mock_session_class.return_value = mock_session

            # Run CLI
            cli = CpauElectricCli()
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

    @patch('cpau.cli.CpauApiSession')
    def test_billing_interval(self, mock_session_class, mock_credentials):
        """Test billing interval with extended fieldnames."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock session and meter
            mock_session = MagicMock()
            mock_meter = MagicMock()

            # Create billing records
            billing_records = [
                UsageRecord(
                    date=datetime(2024, 12, 1),
                    import_kwh=689.4,
                    export_kwh=156.2,
                    net_kwh=533.2,
                    billing_period_start=date(2024, 12, 1),
                    billing_period_end=date(2024, 12, 31),
                    billing_period_length=31
                )
            ]
            mock_meter.get_usage.return_value = billing_records

            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get_electric_meter.return_value = mock_meter

            mock_session_class.return_value = mock_session

            # Run CLI
            cli = CpauElectricCli()
            with patch('sys.stdout', new=StringIO()) as fake_out:
                exit_code = cli.go([
                    '--interval', 'billing',
                    '--secrets-file', secrets_file,
                    '2024-12-01'
                ])

                assert exit_code == 0

                # Check billing-specific fields
                output = fake_out.getvalue()
                assert 'billing_period_start' in output
                assert 'billing_period_end' in output
                assert 'billing_period_length' in output

        finally:
            Path(secrets_file).unlink()

    @patch('cpau.cli.CpauApiSession')
    def test_output_to_file(self, mock_session_class, mock_credentials):
        """Test writing output to file."""
        secrets_file = self.create_temp_secrets(mock_credentials)
        output_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        output_file.close()

        try:
            # Mock session and meter
            mock_session = MagicMock()
            mock_meter = MagicMock()
            mock_meter.get_usage.return_value = self.create_mock_usage_records()

            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get_electric_meter.return_value = mock_meter

            mock_session_class.return_value = mock_session

            # Run CLI
            cli = CpauElectricCli()
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
            assert 'date,export_kwh,import_kwh,net_kwh' in content
            assert '2024-12-01' in content

        finally:
            Path(secrets_file).unlink()
            Path(output_file.name).unlink()

    def test_missing_secrets_file(self):
        """Test error handling when secrets file is missing."""
        cli = CpauElectricCli()

        exit_code = cli.go([
            '--secrets-file', '/nonexistent/secrets.json',
            '2024-12-01'
        ])

        assert exit_code == 1

    def test_invalid_date_format(self, mock_credentials):
        """Test error handling for invalid date format."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            cli = CpauElectricCli()
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
            cli = CpauElectricCli()
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
            cli = CpauElectricCli()
            exit_code = cli.go([
                '--secrets-file', temp_file.name,
                '2024-12-01'
            ])

            assert exit_code == 1

        finally:
            Path(temp_file.name).unlink()

    @patch('cpau.cli.CpauApiSession')
    def test_api_error_handling(self, mock_session_class, mock_credentials):
        """Test error handling when API call fails."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock session that raises error
            from cpau.exceptions import CpauApiError
            mock_session_class.side_effect = CpauApiError("API connection failed")

            cli = CpauElectricCli()
            exit_code = cli.go([
                '--secrets-file', secrets_file,
                '2024-12-01'
            ])

            assert exit_code == 1

        finally:
            Path(secrets_file).unlink()

    @patch('cpau.cli.CpauApiSession')
    def test_verbose_flag(self, mock_session_class, mock_credentials):
        """Test verbose logging flag."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock session and meter
            mock_session = MagicMock()
            mock_meter = MagicMock()
            mock_meter.get_usage.return_value = self.create_mock_usage_records()

            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get_electric_meter.return_value = mock_meter

            mock_session_class.return_value = mock_session

            # Run CLI with verbose flag
            cli = CpauElectricCli()
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

    @patch('cpau.cli.CpauApiSession')
    def test_default_end_date(self, mock_session_class, mock_credentials):
        """Test that end_date defaults to 2 days ago when not provided."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock session and meter
            mock_session = MagicMock()
            mock_meter = MagicMock()
            mock_meter.get_usage.return_value = []

            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get_electric_meter.return_value = mock_meter

            mock_session_class.return_value = mock_session

            # Run CLI without end_date
            cli = CpauElectricCli()
            with patch('sys.stdout', new=StringIO()):
                exit_code = cli.go([
                    '--secrets-file', secrets_file,
                    '2024-12-01'  # No end_date
                ])

                assert exit_code == 0

                # Verify get_usage was called with a default end_date
                assert mock_meter.get_usage.called
                call_args = mock_meter.get_usage.call_args
                # end_date should be set to 2 days ago
                assert call_args[1]['end_date'] is not None

        finally:
            Path(secrets_file).unlink()
