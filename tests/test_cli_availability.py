"""Tests for cpau-availability CLI."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import date
from io import StringIO

from cpau.cli import CpauAvailabilityCli


@pytest.mark.unit
class TestCpauAvailabilityCli:
    """Tests for cpau-availability command-line interface."""

    def create_temp_secrets(self, credentials):
        """Create a temporary secrets file."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(credentials, temp_file)
        temp_file.close()
        return temp_file.name

    @patch('cpau.cli.CpauWaterMeter')
    @patch('cpau.cli.CpauApiSession')
    def test_basic_availability_check(self, mock_session_class, mock_water_meter_class, mock_credentials):
        """Test basic availability check for both electric and water meters."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock electric meter session
            mock_session = MagicMock()
            mock_electric_meter = MagicMock()
            mock_electric_meter.meter_number = "12345678"
            mock_electric_meter.get_available_intervals.return_value = ['billing', 'daily', 'hourly']
            mock_electric_meter.get_availability_window.side_effect = [
                (date(2020, 1, 1), date(2024, 12, 31)),  # billing
                (date(2020, 1, 1), date(2024, 12, 31)),  # daily
                (date(2024, 10, 1), date(2024, 12, 31)),  # hourly
            ]

            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get_electric_meter.return_value = mock_electric_meter
            mock_session_class.return_value = mock_session

            # Mock water meter
            mock_water_meter = MagicMock()
            mock_water_meter.get_available_intervals.return_value = ['billing', 'daily', 'hourly']
            mock_water_meter.get_availability_window.side_effect = [
                (date(2017, 1, 1), date(2024, 12, 31)),  # billing
                (date(2017, 1, 1), date(2024, 12, 31)),  # daily
                (date(2024, 10, 1), date(2024, 12, 31)),  # hourly
            ]
            mock_water_meter_class.return_value = mock_water_meter

            # Run CLI
            cli = CpauAvailabilityCli()
            with patch('sys.stdout', new=StringIO()) as fake_out:
                exit_code = cli.go(['--secrets-file', secrets_file])

                # Check exit code
                assert exit_code == 0

                # Check CSV output
                output = fake_out.getvalue()
                assert 'data_type,interval,data_start,data_end' in output
                assert 'electric,billing' in output
                assert 'electric,daily' in output
                assert 'electric,hourly' in output
                assert 'water,billing' in output
                assert 'water,daily' in output
                assert 'water,hourly' in output
                assert '2020-01-01' in output
                assert '2017-01-01' in output

        finally:
            Path(secrets_file).unlink()

    @patch('cpau.cli.CpauWaterMeter')
    @patch('cpau.cli.CpauApiSession')
    def test_output_to_file(self, mock_session_class, mock_water_meter_class, mock_credentials):
        """Test writing output to file."""
        secrets_file = self.create_temp_secrets(mock_credentials)
        output_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        output_file.close()

        try:
            # Mock electric meter session
            mock_session = MagicMock()
            mock_electric_meter = MagicMock()
            mock_electric_meter.meter_number = "12345678"
            mock_electric_meter.get_available_intervals.return_value = ['daily']
            mock_electric_meter.get_availability_window.return_value = (date(2020, 1, 1), date(2024, 12, 31))

            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get_electric_meter.return_value = mock_electric_meter
            mock_session_class.return_value = mock_session

            # Mock water meter
            mock_water_meter = MagicMock()
            mock_water_meter.get_available_intervals.return_value = ['daily']
            mock_water_meter.get_availability_window.return_value = (date(2017, 1, 1), date(2024, 12, 31))
            mock_water_meter_class.return_value = mock_water_meter

            # Run CLI
            cli = CpauAvailabilityCli()
            exit_code = cli.go([
                '--secrets-file', secrets_file,
                '--output-file', output_file.name
            ])

            assert exit_code == 0

            # Verify output file was created and has content
            output_path = Path(output_file.name)
            assert output_path.exists()
            content = output_path.read_text()
            assert 'data_type,interval,data_start,data_end' in content
            assert 'electric,daily' in content
            assert 'water,daily' in content

        finally:
            Path(secrets_file).unlink()
            Path(output_file.name).unlink()

    @patch('cpau.cli.CpauWaterMeter')
    @patch('cpau.cli.CpauApiSession')
    def test_electric_only_success(self, mock_session_class, mock_water_meter_class, mock_credentials):
        """Test when only electric meter succeeds."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock electric meter session (succeeds)
            mock_session = MagicMock()
            mock_electric_meter = MagicMock()
            mock_electric_meter.meter_number = "12345678"
            mock_electric_meter.get_available_intervals.return_value = ['daily']
            mock_electric_meter.get_availability_window.return_value = (date(2020, 1, 1), date(2024, 12, 31))

            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get_electric_meter.return_value = mock_electric_meter
            mock_session_class.return_value = mock_session

            # Mock water meter (fails)
            mock_water_meter_class.side_effect = Exception("Water meter connection failed")

            # Run CLI
            cli = CpauAvailabilityCli()
            with patch('sys.stdout', new=StringIO()) as fake_out:
                exit_code = cli.go(['--secrets-file', secrets_file])

                # Should still succeed with partial data
                assert exit_code == 0

                # Check output contains electric data
                output = fake_out.getvalue()
                assert 'electric,daily' in output
                # Should not contain water data
                assert 'water,daily' not in output

        finally:
            Path(secrets_file).unlink()

    @patch('cpau.cli.CpauWaterMeter')
    @patch('cpau.cli.CpauApiSession')
    def test_water_only_success(self, mock_session_class, mock_water_meter_class, mock_credentials):
        """Test when only water meter succeeds."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock electric meter session (fails)
            from cpau.exceptions import CpauApiError
            mock_session_class.side_effect = CpauApiError("Electric meter connection failed")

            # Mock water meter (succeeds)
            mock_water_meter = MagicMock()
            mock_water_meter.get_available_intervals.return_value = ['daily']
            mock_water_meter.get_availability_window.return_value = (date(2017, 1, 1), date(2024, 12, 31))
            mock_water_meter_class.return_value = mock_water_meter

            # Run CLI
            cli = CpauAvailabilityCli()
            with patch('sys.stdout', new=StringIO()) as fake_out:
                exit_code = cli.go(['--secrets-file', secrets_file])

                # Should still succeed with partial data
                assert exit_code == 0

                # Check output contains water data
                output = fake_out.getvalue()
                assert 'water,daily' in output
                # Should not contain electric data
                assert 'electric,daily' not in output

        finally:
            Path(secrets_file).unlink()

    @patch('cpau.cli.CpauWaterMeter')
    @patch('cpau.cli.CpauApiSession')
    def test_both_meters_fail(self, mock_session_class, mock_water_meter_class, mock_credentials):
        """Test when both meters fail."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock electric meter (fails)
            from cpau.exceptions import CpauApiError
            mock_session_class.side_effect = CpauApiError("Electric meter failed")

            # Mock water meter (fails)
            mock_water_meter_class.side_effect = Exception("Water meter failed")

            # Run CLI
            cli = CpauAvailabilityCli()
            exit_code = cli.go(['--secrets-file', secrets_file])

            # Should fail when both meters fail
            assert exit_code == 1

        finally:
            Path(secrets_file).unlink()

    @patch('cpau.cli.CpauWaterMeter')
    @patch('cpau.cli.CpauApiSession')
    def test_some_intervals_fail(self, mock_session_class, mock_water_meter_class, mock_credentials):
        """Test when some interval checks fail but others succeed."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock electric meter session
            mock_session = MagicMock()
            mock_electric_meter = MagicMock()
            mock_electric_meter.meter_number = "12345678"
            mock_electric_meter.get_available_intervals.return_value = ['billing', 'daily', 'hourly']
            # First succeeds, second fails, third succeeds
            mock_electric_meter.get_availability_window.side_effect = [
                (date(2020, 1, 1), date(2024, 12, 31)),  # billing - success
                Exception("Daily check failed"),          # daily - fails
                (date(2024, 10, 1), date(2024, 12, 31)),  # hourly - success
            ]

            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get_electric_meter.return_value = mock_electric_meter
            mock_session_class.return_value = mock_session

            # Mock water meter (succeeds)
            mock_water_meter = MagicMock()
            mock_water_meter.get_available_intervals.return_value = ['daily']
            mock_water_meter.get_availability_window.return_value = (date(2017, 1, 1), date(2024, 12, 31))
            mock_water_meter_class.return_value = mock_water_meter

            # Run CLI
            cli = CpauAvailabilityCli()
            with patch('sys.stdout', new=StringIO()) as fake_out:
                exit_code = cli.go(['--secrets-file', secrets_file])

                # Should succeed with partial data
                assert exit_code == 0

                # Check output contains successful intervals
                output = fake_out.getvalue()
                assert 'electric,billing' in output
                assert 'electric,hourly' in output
                assert 'water,daily' in output
                # Daily electric should not be in output
                assert 'electric,daily' not in output

        finally:
            Path(secrets_file).unlink()

    @patch('cpau.cli.CpauWaterMeter')
    @patch('cpau.cli.CpauApiSession')
    def test_custom_cache_dir(self, mock_session_class, mock_water_meter_class, mock_credentials):
        """Test using custom cache directory for water meter."""
        secrets_file = self.create_temp_secrets(mock_credentials)
        cache_dir = tempfile.mkdtemp()

        try:
            # Mock electric meter (fails to isolate water meter check)
            from cpau.exceptions import CpauApiError
            mock_session_class.side_effect = CpauApiError("Electric meter failed")

            # Mock water meter
            mock_water_meter = MagicMock()
            mock_water_meter.get_available_intervals.return_value = ['daily']
            mock_water_meter.get_availability_window.return_value = (date(2017, 1, 1), date(2024, 12, 31))
            mock_water_meter_class.return_value = mock_water_meter

            # Run CLI with custom cache dir
            cli = CpauAvailabilityCli()
            with patch('sys.stdout', new=StringIO()):
                exit_code = cli.go([
                    '--secrets-file', secrets_file,
                    '--cache-dir', cache_dir
                ])

                assert exit_code == 0

                # Verify CpauWaterMeter was called with custom cache_dir
                mock_water_meter_class.assert_called_once()
                call_kwargs = mock_water_meter_class.call_args[1]
                assert call_kwargs['cache_dir'] == cache_dir

        finally:
            Path(secrets_file).unlink()
            Path(cache_dir).rmdir()

    def test_missing_secrets_file(self):
        """Test error handling when secrets file is missing."""
        cli = CpauAvailabilityCli()

        exit_code = cli.go(['--secrets-file', '/nonexistent/secrets.json'])

        assert exit_code == 1

    def test_invalid_secrets_json(self):
        """Test error handling for invalid JSON in secrets file."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        temp_file.write("{ invalid json")
        temp_file.close()

        try:
            cli = CpauAvailabilityCli()
            exit_code = cli.go(['--secrets-file', temp_file.name])

            assert exit_code == 1

        finally:
            Path(temp_file.name).unlink()

    def test_missing_credentials_fields(self):
        """Test error handling when secrets file is missing required fields."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump({"userid": "test@example.com"}, temp_file)
        temp_file.close()

        try:
            cli = CpauAvailabilityCli()
            exit_code = cli.go(['--secrets-file', temp_file.name])

            assert exit_code == 1

        finally:
            Path(temp_file.name).unlink()

    @patch('cpau.cli.CpauWaterMeter')
    @patch('cpau.cli.CpauApiSession')
    def test_verbose_flag(self, mock_session_class, mock_water_meter_class, mock_credentials):
        """Test verbose logging flag."""
        secrets_file = self.create_temp_secrets(mock_credentials)

        try:
            # Mock electric meter session
            mock_session = MagicMock()
            mock_electric_meter = MagicMock()
            mock_electric_meter.meter_number = "12345678"
            mock_electric_meter.get_available_intervals.return_value = ['daily']
            mock_electric_meter.get_availability_window.return_value = (date(2020, 1, 1), date(2024, 12, 31))

            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get_electric_meter.return_value = mock_electric_meter
            mock_session_class.return_value = mock_session

            # Mock water meter
            mock_water_meter = MagicMock()
            mock_water_meter.get_available_intervals.return_value = ['daily']
            mock_water_meter.get_availability_window.return_value = (date(2017, 1, 1), date(2024, 12, 31))
            mock_water_meter_class.return_value = mock_water_meter

            # Run CLI with verbose flag
            cli = CpauAvailabilityCli()
            with patch('sys.stdout', new=StringIO()):
                exit_code = cli.go([
                    '--verbose',
                    '--secrets-file', secrets_file
                ])

                assert exit_code == 0

        finally:
            Path(secrets_file).unlink()
