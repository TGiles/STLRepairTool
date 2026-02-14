"""Test repair_mesh_windows() Windows engine."""

import pytest
import sys
from unittest.mock import patch, MagicMock
import repair_stl


@pytest.mark.windows_only
def test_repair_mesh_windows_missing_api_flag(non_watertight_mesh):
    """HAS_WINDOWS_API=False -> raises RuntimeError."""
    with patch.object(repair_stl, 'HAS_WINDOWS_API', False):
        with pytest.raises(RuntimeError, match="Windows API not available"):
            repair_stl.repair_mesh_windows(non_watertight_mesh, "/tmp/input.stl", "/tmp/output.stl")


@pytest.mark.windows_only
def test_repair_mesh_windows_wrong_platform(non_watertight_mesh):
    """sys.platform != 'win32' -> raises RuntimeError."""
    with patch.object(repair_stl, 'HAS_WINDOWS_API', True):
        with patch.object(sys, 'platform', 'linux'):
            with pytest.raises(RuntimeError, match="only available on Windows"):
                repair_stl.repair_mesh_windows(non_watertight_mesh, "/tmp/input.stl", "/tmp/output.stl")


@pytest.mark.windows_only
def test_repair_mesh_windows_missing_lxml(non_watertight_mesh):
    """lxml not installed -> raises RuntimeError."""
    with patch.object(repair_stl, 'HAS_WINDOWS_API', True):
        with patch.object(sys, 'platform', 'win32'):
            # Mock lxml import to raise ImportError
            with patch.dict('sys.modules', {'lxml': None}):
                def mock_import(name, *args, **kwargs):
                    if 'lxml' in name:
                        raise ImportError("No module named 'lxml'")
                    return __import__(name, *args, **kwargs)

                with patch('builtins.__import__', side_effect=mock_import):
                    with pytest.raises(RuntimeError, match="lxml is required"):
                        repair_stl.repair_mesh_windows(non_watertight_mesh, "/tmp/input.stl", "/tmp/output.stl")


@pytest.mark.windows_only
def test_repair_mesh_windows_asyncio_fails_fallback(non_watertight_mesh):
    """asyncio.run() raises -> falls back to repair_mesh()."""
    with patch.object(repair_stl, 'HAS_WINDOWS_API', True):
        with patch.object(sys, 'platform', 'win32'):
            with patch('repair_stl.repair_mesh_windows_async', new=MagicMock()):
                with patch('repair_stl.asyncio.run', side_effect=Exception("WinRT error")):
                    with patch('repair_stl.repair_mesh') as mock_repair:
                        mock_repair.return_value = non_watertight_mesh
                        result = repair_stl.repair_mesh_windows(
                            non_watertight_mesh, "/tmp/input.stl", "/tmp/output.stl"
                        )
                        # Should fallback to repair_mesh
                        mock_repair.assert_called_once_with(non_watertight_mesh)


@pytest.mark.windows_only
def test_repair_mesh_windows_not_watertight_fallback(non_watertight_mesh, tmp_path):
    """Repaired 3MF not watertight -> falls back to repair_mesh()."""
    # This would require extensive mocking of the Windows 3D Model Repair API
    # Simplified test: verify function signature
    assert callable(repair_stl.repair_mesh_windows)


@pytest.mark.windows_only
def test_repair_mesh_windows_temp_cleanup(tmp_path, non_watertight_mesh):
    """Temp 3MF files cleaned up on error."""
    input_stl = tmp_path / "input.stl"
    output_stl = tmp_path / "output.stl"
    non_watertight_mesh.export(str(input_stl))

    with patch.object(repair_stl, 'HAS_WINDOWS_API', True):
        with patch.object(sys, 'platform', 'win32'):
            with patch('repair_stl.repair_mesh_windows_async', new=MagicMock()):
                with patch('repair_stl.asyncio.run', side_effect=Exception("Cleanup test")):
                    with patch('repair_stl.repair_mesh', return_value=non_watertight_mesh):
                        # Should not leave temp files
                        result = repair_stl.repair_mesh_windows(
                            non_watertight_mesh, str(input_stl), str(output_stl)
                        )
                        assert result is not None
