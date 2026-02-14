"""Test that fixture meshes have expected properties."""

import trimesh


def test_watertight_mesh_properties(watertight_mesh):
    """Verify watertight mesh is actually watertight."""
    assert isinstance(watertight_mesh, trimesh.Trimesh)
    assert watertight_mesh.is_watertight
    assert len(watertight_mesh.faces) == 12  # Box has 12 triangular faces
    assert len(watertight_mesh.vertices) == 8  # Box has 8 vertices


def test_non_watertight_mesh_properties(non_watertight_mesh):
    """Verify non-watertight mesh is not watertight."""
    assert isinstance(non_watertight_mesh, trimesh.Trimesh)
    assert not non_watertight_mesh.is_watertight
    assert len(non_watertight_mesh.faces) > 0  # Has some faces


def test_watertight_stl_file_loads(watertight_stl):
    """Verify watertight STL file can be loaded."""
    mesh = trimesh.load(watertight_stl)
    assert mesh.is_watertight


def test_non_watertight_stl_file_loads(non_watertight_stl):
    """Verify non-watertight STL file can be loaded."""
    mesh = trimesh.load(non_watertight_stl)
    assert not mesh.is_watertight
