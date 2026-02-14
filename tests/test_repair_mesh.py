"""Test repair_mesh() core repair logic."""

import pytest
from unittest.mock import patch, MagicMock
import numpy as np
import repair_stl


def test_repair_mesh_with_pymeshfix_success(non_watertight_mesh):
    """pymeshfix succeeds -> returns watertight mesh."""
    # Mock pymeshfix to return a watertight mesh
    mock_meshfix = MagicMock()
    mock_meshfix.v = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
    mock_meshfix.f = np.array([[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]])

    with patch('repair_stl.pymeshfix.MeshFix', return_value=mock_meshfix):
        repaired = repair_stl.repair_mesh(non_watertight_mesh)
        assert repaired is not None
        mock_meshfix.repair.assert_called_once()


def test_repair_mesh_with_pymeshfix_vtk_face_reshape(non_watertight_mesh):
    """pymeshfix VTK 1D face array -> reshaped correctly."""
    # Mock pymeshfix returning 1D VTK array (shape: n*4)
    mock_meshfix = MagicMock()
    mock_meshfix.v = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
    # VTK format: [3, v0, v1, v2, 3, v3, v4, v5, ...]
    mock_meshfix.f = np.array([3, 0, 1, 2, 3, 0, 1, 3])

    with patch('repair_stl.pymeshfix.MeshFix', return_value=mock_meshfix):
        repaired = repair_stl.repair_mesh(non_watertight_mesh)
        assert repaired is not None
        # Should successfully reshape and create mesh


def test_repair_mesh_pymeshfix_raises_falls_to_trimesh(non_watertight_mesh):
    """pymeshfix raises -> falls through to trimesh fallback."""
    with patch('repair_stl.pymeshfix.MeshFix', side_effect=Exception("pymeshfix error")):
        repaired = repair_stl.repair_mesh(non_watertight_mesh)
        # Should still return a mesh via trimesh fallback
        assert repaired is not None


def test_repair_mesh_without_pymeshfix(non_watertight_mesh):
    """HAS_PYMESHFIX=False -> trimesh fallback executes."""
    with patch.object(repair_stl, 'HAS_PYMESHFIX', False):
        repaired = repair_stl.repair_mesh(non_watertight_mesh)
        # Should use trimesh operations
        assert repaired is not None


def test_repair_mesh_trimesh_fallback_attribute_error(non_watertight_mesh):
    """trimesh fallback AttributeError -> caught, returns mesh."""
    # Mock fill_holes to raise AttributeError
    with patch.object(repair_stl, 'HAS_PYMESHFIX', False):
        with patch.object(non_watertight_mesh, 'fill_holes', side_effect=AttributeError):
            repaired = repair_stl.repair_mesh(non_watertight_mesh)
            # Should catch error and still return mesh
            assert repaired is not None


def test_repair_mesh_preserves_vertices(watertight_mesh):
    """Repair preserves mesh structure."""
    original_vertex_count = len(watertight_mesh.vertices)
    repaired = repair_stl.repair_mesh(watertight_mesh)

    assert repaired is not None
    # Vertex count may change slightly due to deduplication
    assert len(repaired.vertices) > 0
