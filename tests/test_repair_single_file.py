"""Test repair_single_file() function."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import trimesh
import repair_stl


def test_repair_single_file_success(tmp_path, non_watertight_mesh, watertight_mesh):
    """Successful repair -> REPAIRED status, output file exists."""
    input_path = tmp_path / "input.stl"
    output_path = tmp_path / "output.stl"
    non_watertight_mesh.export(str(input_path))

    with patch('repair_stl.repair_mesh', return_value=watertight_mesh):
        result = repair_stl.repair_single_file(
            str(input_path), str(output_path), "local"
        )

    assert result.status == repair_stl.FileStatus.REPAIRED
    assert Path(output_path).exists()
    assert result.output_size > 0


def test_repair_single_file_in_place(tmp_path, non_watertight_mesh, watertight_mesh):
    """In-place repair (input == output) works correctly."""
    input_path = tmp_path / "inplace.stl"
    non_watertight_mesh.export(str(input_path))

    with patch('repair_stl.repair_mesh', return_value=watertight_mesh):
        result = repair_stl.repair_single_file(
            str(input_path), str(input_path), "local"
        )

    assert result.status == repair_stl.FileStatus.REPAIRED
    assert Path(input_path).exists()


def test_repair_single_file_corrupt_input(tmp_path):
    """Corrupt input -> FAILED status, no output file."""
    input_path = tmp_path / "corrupt.stl"
    output_path = tmp_path / "output.stl"

    # Create STL file - we'll mock trimesh.load to raise exception
    input_path.write_bytes(b'\x00\xFF\xFE\xFD\xFC\xFB' * 100)

    with patch('repair_stl.trimesh.load', side_effect=Exception("Cannot load corrupted file")):
        result = repair_stl.repair_single_file(
            str(input_path), str(output_path), "local"
        )

    assert result.status == repair_stl.FileStatus.FAILED
    assert not Path(output_path).exists()
    assert result.error_message != ""


def test_repair_single_file_repair_raises(tmp_path, non_watertight_mesh):
    """Repair raises -> FAILED, no temp .stl.tmp remains."""
    input_path = tmp_path / "input.stl"
    output_path = tmp_path / "output.stl"
    non_watertight_mesh.export(str(input_path))

    with patch('repair_stl.repair_mesh', side_effect=Exception("Repair failed")):
        result = repair_stl.repair_single_file(
            str(input_path), str(output_path), "local"
        )

    assert result.status == repair_stl.FileStatus.FAILED
    assert not Path(output_path).exists()
    # Verify no temp files left behind
    temp_files = list(tmp_path.glob("*.stl.tmp"))
    assert len(temp_files) == 0


def test_repair_single_file_export_raises(tmp_path, non_watertight_mesh, watertight_mesh):
    """Export raises -> FAILED, no temp .stl.tmp remains."""
    input_path = tmp_path / "input.stl"
    output_path = tmp_path / "output.stl"
    non_watertight_mesh.export(str(input_path))

    # Mock export to raise exception
    mock_mesh = MagicMock(spec=trimesh.Trimesh)
    mock_mesh.export.side_effect = Exception("Export failed")

    with patch('repair_stl.repair_mesh', return_value=mock_mesh):
        result = repair_stl.repair_single_file(
            str(input_path), str(output_path), "local"
        )

    assert result.status == repair_stl.FileStatus.FAILED
    # Verify no temp files left behind
    temp_files = list(tmp_path.glob("*.stl.tmp"))
    assert len(temp_files) == 0


def test_repair_single_file_windows_engine(tmp_path, non_watertight_mesh, watertight_mesh):
    """engine='windows' -> dispatches to repair_mesh_windows()."""
    input_path = tmp_path / "input.stl"
    output_path = tmp_path / "output.stl"
    non_watertight_mesh.export(str(input_path))

    with patch('repair_stl.repair_mesh_windows', return_value=watertight_mesh) as mock_win:
        result = repair_stl.repair_single_file(
            str(input_path), str(output_path), "windows"
        )

    mock_win.assert_called_once()
    assert result.status == repair_stl.FileStatus.REPAIRED


def test_repair_single_file_keyboard_interrupt_cleanup(tmp_path, non_watertight_mesh):
    """KeyboardInterrupt -> cleans up temp, re-raises."""
    input_path = tmp_path / "input.stl"
    output_path = tmp_path / "output.stl"
    non_watertight_mesh.export(str(input_path))

    with patch('repair_stl.repair_mesh', side_effect=KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            repair_stl.repair_single_file(str(input_path), str(output_path), "local")

    # Verify no temp files left behind
    temp_files = list(tmp_path.glob("*.stl.tmp"))
    assert len(temp_files) == 0


def test_repair_single_file_default_engine(tmp_path, non_watertight_mesh, watertight_mesh):
    """Default engine uses repair_mesh()."""
    input_path = tmp_path / "input.stl"
    output_path = tmp_path / "output.stl"
    non_watertight_mesh.export(str(input_path))

    with patch('repair_stl.repair_mesh', return_value=watertight_mesh) as mock_repair:
        result = repair_stl.repair_single_file(
            str(input_path), str(output_path), "local"
        )

    mock_repair.assert_called_once()
    assert result.status == repair_stl.FileStatus.REPAIRED
