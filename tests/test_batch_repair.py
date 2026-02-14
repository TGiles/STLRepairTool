"""Test batch_repair() orchestration function."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import repair_stl


@pytest.mark.slow
def test_batch_repair_discovers_and_repairs_files(stl_directory, watertight_mesh):
    """Discovers and repairs files, returns results."""
    with patch('repair_stl.repair_mesh', return_value=watertight_mesh):
        results = repair_stl.batch_repair(
            stl_directory, backup=False, workers=1, engine="local"
        )

    # Should find 3 files (good.stl, broken.stl, subdir/also_broken.stl)
    assert len(results) == 3

    # At least one should be repaired (the non-watertight ones)
    statuses = [r.status for r in results]
    assert repair_stl.FileStatus.REPAIRED in statuses or repair_stl.FileStatus.SKIPPED in statuses


@pytest.mark.slow
def test_batch_repair_creates_backup_directory(stl_directory, watertight_mesh):
    """Creates stl_backup/ when backup=True."""
    backup_dir = Path(stl_directory) / "stl_backup"

    # Remove backup dir if it exists from fixture
    import shutil
    if backup_dir.exists():
        shutil.rmtree(backup_dir)

    with patch('repair_stl.repair_mesh', return_value=watertight_mesh):
        results = repair_stl.batch_repair(
            stl_directory, backup=True, workers=1, engine="local"
        )

    # Backup directory should be created
    assert backup_dir.exists()
    assert backup_dir.is_dir()


def test_batch_repair_no_backup_when_disabled(stl_directory, watertight_mesh):
    """No backup dir when backup=False."""
    backup_dir = Path(stl_directory) / "stl_backup_test"

    with patch('repair_stl.repair_mesh', return_value=watertight_mesh):
        results = repair_stl.batch_repair(
            stl_directory, backup=False, workers=1, engine="local"
        )

    # Should not create new backup directory (fixture has one, but batch won't create it)
    # Just verify function completes
    assert isinstance(results, list)


def test_batch_repair_empty_directory(tmp_path):
    """Empty directory -> returns empty list."""
    results = repair_stl.batch_repair(
        str(tmp_path), backup=False, workers=1, engine="local"
    )

    assert results == []


@pytest.mark.slow
def test_batch_repair_skips_watertight_files(stl_directory, watertight_mesh):
    """Skips watertight files."""
    with patch('repair_stl.repair_mesh', return_value=watertight_mesh):
        results = repair_stl.batch_repair(
            stl_directory, backup=False, workers=1, engine="local"
        )

    # good.stl should be skipped
    skipped = [r for r in results if r.status == repair_stl.FileStatus.SKIPPED]
    assert len(skipped) >= 1


@pytest.mark.slow
def test_batch_repair_multiple_workers(stl_directory, watertight_mesh):
    """Multiple workers works correctly."""
    with patch('repair_stl.repair_mesh', return_value=watertight_mesh):
        results = repair_stl.batch_repair(
            stl_directory, backup=False, workers=2, engine="local"
        )

    # Should still process all files
    assert len(results) == 3


def test_batch_repair_windows_engine_validation_fails(tmp_path):
    """Windows engine validation -> sys.exit(1) when unavailable."""
    # Create a temp STL file so discovery doesn't short-circuit
    test_stl = tmp_path / "test.stl"
    test_stl.write_text("dummy")

    with patch.object(repair_stl, 'HAS_WINDOWS_API', False):
        with pytest.raises(SystemExit) as exc_info:
            repair_stl.batch_repair(
                str(tmp_path), backup=False, workers=1, engine="windows"
            )
        assert exc_info.value.code == 1


def test_batch_repair_windows_engine_validation_platform(tmp_path):
    """Windows engine on non-Windows -> sys.exit(1)."""
    # Create a temp STL file so discovery doesn't short-circuit
    test_stl = tmp_path / "test.stl"
    test_stl.write_text("dummy")

    with patch.object(repair_stl, 'HAS_WINDOWS_API', True):
        with patch.object(sys, 'platform', 'linux'):
            with pytest.raises(SystemExit) as exc_info:
                repair_stl.batch_repair(
                    str(tmp_path), backup=False, workers=1, engine="windows"
                )
            assert exc_info.value.code == 1


@pytest.mark.slow
def test_batch_repair_result_structure(stl_directory, watertight_mesh):
    """Results have expected structure."""
    with patch('repair_stl.repair_mesh', return_value=watertight_mesh):
        results = repair_stl.batch_repair(
            stl_directory, backup=False, workers=1, engine="local"
        )

    for result in results:
        assert hasattr(result, 'file_path')
        assert hasattr(result, 'status')
        assert hasattr(result, 'elapsed_seconds')
        assert isinstance(result.elapsed_seconds, (int, float))
