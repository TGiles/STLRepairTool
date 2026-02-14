"""Test __main__ entry point execution."""

import subprocess
import sys
from pathlib import Path


def test_main_entry_point_help(tmp_path):
    """Script executes when run as __main__ and shows help."""
    # Run the script directly as a subprocess
    result = subprocess.run(
        [sys.executable, "repair_stl.py"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent  # Run from project root
    )

    # Should exit with error code (no args provided)
    assert result.returncode == 1

    # Should display usage/help information
    assert "usage" in result.stdout.lower() or "repair" in result.stdout.lower()


def test_main_entry_point_check_watertight(tmp_path, watertight_stl):
    """Script executes check-watertight mode when run directly."""
    result = subprocess.run(
        [sys.executable, "repair_stl.py", "--check-watertight", watertight_stl],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )

    # Should exit successfully
    assert result.returncode == 0

    # Should output True for watertight file
    assert "true" in result.stdout.lower()


def test_main_entry_point_invalid_args(tmp_path):
    """Script handles invalid arguments when run directly."""
    result = subprocess.run(
        [sys.executable, "repair_stl.py", "--invalid-flag"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )

    # Should exit with error
    assert result.returncode != 0

    # Should show error message
    assert "error" in result.stderr.lower() or "invalid" in result.stderr.lower()


def test_main_entry_point_version_info():
    """Script is executable and responds to basic invocation."""
    # Just verify the script can be executed without syntax errors
    result = subprocess.run(
        [sys.executable, "-c", "import repair_stl; print(repair_stl.__file__)"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )

    assert result.returncode == 0
    assert "repair_stl.py" in result.stdout
