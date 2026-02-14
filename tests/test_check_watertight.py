"""Test check_watertight() function."""

import pytest
import repair_stl


def test_check_watertight_with_watertight_file(watertight_stl):
    """Watertight file returns True."""
    assert repair_stl.check_watertight(watertight_stl) is True


def test_check_watertight_with_non_watertight_file(non_watertight_stl):
    """Non-watertight file returns False."""
    assert repair_stl.check_watertight(non_watertight_stl) is False


def test_check_watertight_with_nonexistent_file():
    """Nonexistent file raises exception."""
    with pytest.raises(Exception):
        repair_stl.check_watertight("/nonexistent/file.stl")
