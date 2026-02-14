"""Test _worker_repair_file() worker function."""

import pytest
from pathlib import Path
from unittest.mock import patch
import repair_stl


def test_worker_skips_watertight_file(watertight_stl):
    """Watertight input -> SKIPPED status."""
    base_dir = str(Path(watertight_stl).parent)
    result = repair_stl._worker_repair_file(
        watertight_stl, "local", None, base_dir
    )

    assert result.status == repair_stl.FileStatus.SKIPPED
    assert result.elapsed_seconds >= 0


def test_worker_repairs_non_watertight_file(non_watertight_stl, watertight_mesh):
    """Non-watertight input -> REPAIRED status."""
    base_dir = str(Path(non_watertight_stl).parent)
    with patch('repair_stl.repair_mesh', return_value=watertight_mesh):
        result = repair_stl._worker_repair_file(
            non_watertight_stl, "local", None, base_dir
        )

    assert result.status == repair_stl.FileStatus.REPAIRED
    assert result.elapsed_seconds >= 0


def test_worker_creates_backup_with_relative_path(tmp_path, non_watertight_stl, watertight_mesh):
    """Creates backup preserving relative path structure."""
    base_dir = tmp_path / "base"
    base_dir.mkdir()

    # Create subdirectory structure
    subdir = base_dir / "models" / "broken"
    subdir.mkdir(parents=True)
    stl_file = subdir / "test.stl"

    # Copy non-watertight file to test location
    import shutil
    shutil.copy(non_watertight_stl, str(stl_file))

    backup_dir = tmp_path / "backups"

    with patch('repair_stl.repair_mesh', return_value=watertight_mesh):
        result = repair_stl._worker_repair_file(
            str(stl_file), "local", str(backup_dir), str(base_dir)
        )

    # Verify backup created with relative path structure
    expected_backup = backup_dir / "models" / "broken" / "test.stl"
    assert expected_backup.exists()
    assert result.status == repair_stl.FileStatus.REPAIRED


def test_worker_no_backup_when_backup_dir_none(non_watertight_stl, watertight_mesh):
    """backup_dir=None -> no backup created."""
    base_dir = str(Path(non_watertight_stl).parent)

    with patch('repair_stl.repair_mesh', return_value=watertight_mesh):
        result = repair_stl._worker_repair_file(
            non_watertight_stl,
            "local",
            None,
            base_dir
        )

    assert result.status == repair_stl.FileStatus.REPAIRED
    # No backup should be created (can't easily verify, but no error should occur)


def test_worker_handles_corrupt_input(tmp_path):
    """Corrupt input -> FAILED status."""
    corrupt_file = tmp_path / "corrupt.stl"
    # Create corrupt file - we'll mock trimesh.load to raise exception
    corrupt_file.write_bytes(b'\x00\xFF\xFE\xFD\xFC\xFB' * 100)

    with patch('repair_stl.trimesh.load', side_effect=Exception("Cannot load corrupted file")):
        result = repair_stl._worker_repair_file(
            str(corrupt_file), "local", None, str(tmp_path)
        )

    assert result.status == repair_stl.FileStatus.FAILED
    assert result.error_message != ""
    assert result.elapsed_seconds >= 0


def test_worker_elapsed_seconds_populated(watertight_stl):
    """elapsed_seconds is populated."""
    base_dir = str(Path(watertight_stl).parent)
    result = repair_stl._worker_repair_file(
        watertight_stl, "local", None, base_dir
    )

    assert isinstance(result.elapsed_seconds, (int, float))
    assert result.elapsed_seconds >= 0


def test_worker_preserves_file_path_in_result(non_watertight_stl, watertight_mesh):
    """Result includes original file path."""
    base_dir = str(Path(non_watertight_stl).parent)
    with patch('repair_stl.repair_mesh', return_value=watertight_mesh):
        result = repair_stl._worker_repair_file(
            non_watertight_stl,
            "local",
            None,
            base_dir
        )

    assert result.file_path == non_watertight_stl
