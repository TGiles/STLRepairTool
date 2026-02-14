"""Test CLI argument parsing and mode dispatch."""

import pytest
import sys
import io
from contextlib import redirect_stdout
from unittest.mock import patch, MagicMock
import repair_stl


def test_cli_check_watertight_with_file(watertight_stl):
    """--check-watertight <file> -> prints True/False, exits 0."""
    with patch.object(sys, 'argv', ['repair_stl.py', '--check-watertight', watertight_stl]):
        output = io.StringIO()
        with redirect_stdout(output):
            with pytest.raises(SystemExit) as exc_info:
                repair_stl.main()

        assert exc_info.value.code == 0
        assert "true" in output.getvalue().lower()


def test_cli_check_watertight_without_file(stl_directory):
    """--check-watertight (no file) -> scans CWD."""
    with patch.object(sys, 'argv', ['repair_stl.py', '--check-watertight']):
        with patch('repair_stl.discover_stl_files', return_value=['test.stl']):
            with patch('repair_stl.check_watertight', return_value=True):
                output = io.StringIO()
                with redirect_stdout(output):
                    with pytest.raises(SystemExit) as exc_info:
                        repair_stl.main()

                assert exc_info.value.code == 0


def test_cli_batch_mode(tmp_path):
    """--batch -> calls batch_repair()."""
    with patch.object(sys, 'argv', ['repair_stl.py', '--batch', str(tmp_path)]):
        with patch('repair_stl.batch_repair', return_value=[]) as mock_batch:
            with patch('repair_stl._print_batch_summary'):
                with pytest.raises(SystemExit) as exc_info:
                    repair_stl.main()

                mock_batch.assert_called_once()
                assert exc_info.value.code == 0


def test_cli_batch_with_workers_and_no_backup(tmp_path):
    """--batch --workers 4 --no-backup -> passes args correctly."""
    with patch.object(sys, 'argv', [
        'repair_stl.py', '--batch', '--workers', '4', '--no-backup'
    ]):
        with patch('repair_stl.batch_repair', return_value=[]) as mock_batch:
            with pytest.raises(SystemExit) as exc_info:
                repair_stl.main()

            # Verify batch_repair called with correct arguments (all kwargs)
            call_args = mock_batch.call_args
            assert call_args[1]['root_dir'] == "."
            assert call_args[1]['backup'] is False
            assert call_args[1]['workers'] == 4
            assert exc_info.value.code == 0


def test_cli_batch_with_windows_engine(tmp_path):
    """--batch --engine windows -> passes engine correctly."""
    with patch.object(sys, 'argv', [
        'repair_stl.py', '--batch', str(tmp_path), '--engine', 'windows'
    ]):
        with patch('repair_stl.batch_repair', return_value=[]) as mock_batch:
            with patch('repair_stl._print_batch_summary'):
                with pytest.raises(SystemExit) as exc_info:
                    repair_stl.main()

                call_args = mock_batch.call_args
                assert call_args[1]['engine'] == 'windows'


def test_cli_no_args_prints_help():
    """No args -> prints help, exits 1."""
    with patch.object(sys, 'argv', ['repair_stl.py']):
        output = io.StringIO()
        with redirect_stdout(output):
            with pytest.raises(SystemExit) as exc_info:
                repair_stl.main()

        assert exc_info.value.code == 1
        # Should print usage information
        output_text = output.getvalue()
        assert "usage" in output_text.lower() or "repair" in output_text.lower()


def test_cli_single_file_input_output(tmp_path, non_watertight_stl):
    """<input> <output> -> calls repair_single_file()."""
    output_path = tmp_path / "output.stl"

    with patch.object(sys, 'argv', [
        'repair_stl.py', non_watertight_stl, str(output_path)
    ]):
        with patch('repair_stl.repair_single_file', return_value=repair_stl.RepairResult(
            file_path=str(output_path),
            status=repair_stl.FileStatus.REPAIRED,
            output_size=1000
        )) as mock_repair:
            with pytest.raises(SystemExit) as exc_info:
                repair_stl.main()

            mock_repair.assert_called_once_with(
                non_watertight_stl, str(output_path), 'local'
            )
            assert exc_info.value.code == 0


def test_cli_single_file_input_only_inplace(non_watertight_stl):
    """<input> only -> in-place repair (output defaults to input)."""
    with patch.object(sys, 'argv', ['repair_stl.py', non_watertight_stl]):
        with patch('repair_stl.repair_single_file', return_value=repair_stl.RepairResult(
            file_path=non_watertight_stl,
            status=repair_stl.FileStatus.REPAIRED,
            output_size=1000
        )) as mock_repair:
            with pytest.raises(SystemExit) as exc_info:
                repair_stl.main()

            # Should call with same path for input and output
            mock_repair.assert_called_once_with(
                non_watertight_stl, non_watertight_stl, 'local'
            )
            assert exc_info.value.code == 0


def test_cli_single_file_with_windows_engine(non_watertight_stl, tmp_path):
    """<input> <output> --engine windows -> passes engine."""
    output_path = tmp_path / "output.stl"

    with patch.object(sys, 'argv', [
        'repair_stl.py', non_watertight_stl, str(output_path), '--engine', 'windows'
    ]):
        with patch('repair_stl.repair_single_file', return_value=repair_stl.RepairResult(
            file_path=str(output_path),
            status=repair_stl.FileStatus.REPAIRED,
            output_size=1000
        )) as mock_repair:
            with pytest.raises(SystemExit) as exc_info:
                repair_stl.main()

            call_args = mock_repair.call_args
            assert call_args[0][2] == 'windows'  # Third positional arg is engine


def test_cli_single_file_failed_status():
    """Single file repair FAILED -> exits with non-zero."""
    with patch.object(sys, 'argv', ['repair_stl.py', 'input.stl', 'output.stl']):
        with patch('repair_stl.repair_single_file', return_value=repair_stl.RepairResult(
            file_path='output.stl',
            status=repair_stl.FileStatus.FAILED,
            error_message="Error message"
        )):
            with pytest.raises(SystemExit) as exc_info:
                repair_stl.main()

            # Should exit with error code
            assert exc_info.value.code != 0


def test_cli_batch_keyboard_interrupt(tmp_path):
    """--batch with KeyboardInterrupt -> handles gracefully."""
    with patch.object(sys, 'argv', ['repair_stl.py', '--batch']):
        with patch('repair_stl.batch_repair', side_effect=KeyboardInterrupt):
            # KeyboardInterrupt is not caught in batch mode, so it propagates
            with pytest.raises(KeyboardInterrupt):
                repair_stl.main()
