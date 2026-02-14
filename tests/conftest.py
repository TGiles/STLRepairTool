"""Shared pytest fixtures for repair_stl tests."""

import pytest
import trimesh
from pathlib import Path


@pytest.fixture
def watertight_mesh():
    """Generate a watertight box mesh (12 faces, 8 vertices)."""
    return trimesh.primitives.Box(extents=(1, 1, 1)).to_mesh()


@pytest.fixture
def non_watertight_mesh():
    """Generate a non-watertight sphere mesh with faces removed."""
    sphere = trimesh.primitives.Sphere(radius=1.0, subdivisions=2).to_mesh()
    # Remove 10 faces to make it non-watertight
    broken = trimesh.Trimesh(
        vertices=sphere.vertices,
        faces=sphere.faces[:-10],
        process=True
    )
    return broken


@pytest.fixture
def watertight_stl(tmp_path, watertight_mesh):
    """Export watertight mesh to temporary .stl file."""
    stl_path = tmp_path / "watertight.stl"
    watertight_mesh.export(str(stl_path))
    return str(stl_path)


@pytest.fixture
def non_watertight_stl(tmp_path, non_watertight_mesh):
    """Export non-watertight mesh to temporary .stl file."""
    stl_path = tmp_path / "non_watertight.stl"
    non_watertight_mesh.export(str(stl_path))
    return str(stl_path)


@pytest.fixture
def stl_directory(tmp_path, watertight_mesh, non_watertight_mesh):
    """
    Create a temporary directory structure with multiple STL files:
    - good.stl (watertight)
    - broken.stl (non-watertight)
    - subdir/also_broken.stl (non-watertight)
    - stl_backup/should_ignore.stl (should be excluded)
    """
    # Create main directory files
    good_path = tmp_path / "good.stl"
    broken_path = tmp_path / "broken.stl"
    watertight_mesh.export(str(good_path))
    non_watertight_mesh.export(str(broken_path))

    # Create subdirectory with STL
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    also_broken_path = subdir / "also_broken.stl"
    non_watertight_mesh.export(str(also_broken_path))

    # Create stl_backup directory with file (should be ignored)
    backup_dir = tmp_path / "stl_backup"
    backup_dir.mkdir()
    ignore_path = backup_dir / "should_ignore.stl"
    watertight_mesh.export(str(ignore_path))

    return str(tmp_path)
