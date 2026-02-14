"""Test discover_stl_files() function."""

import repair_stl
from pathlib import Path


def test_discover_finds_all_stl_files(stl_directory):
    """Finds all .stl files recursively in subdirectories."""
    files = repair_stl.discover_stl_files(stl_directory)

    # Should find good.stl, broken.stl, subdir/also_broken.stl
    # Should NOT find stl_backup/should_ignore.stl
    assert len(files) == 3

    filenames = [Path(f).name for f in files]
    assert "good.stl" in filenames
    assert "broken.stl" in filenames
    assert "also_broken.stl" in filenames
    assert "should_ignore.stl" not in filenames


def test_discover_excludes_backup_directory(stl_directory):
    """Excludes stl_backup/ directory."""
    files = repair_stl.discover_stl_files(stl_directory)

    # Verify no files from stl_backup/ are included
    for file_path in files:
        assert "stl_backup" not in file_path


def test_discover_returns_sorted_list(stl_directory):
    """Returns sorted list of files."""
    files = repair_stl.discover_stl_files(stl_directory)
    assert files == sorted(files)


def test_discover_empty_directory(tmp_path):
    """Empty directory returns empty list."""
    files = repair_stl.discover_stl_files(str(tmp_path))
    assert files == []


def test_discover_case_insensitive_extension(tmp_path, watertight_mesh):
    """Matches .STL extension case-insensitively."""
    # Create file with uppercase extension
    upper_stl = tmp_path / "test.STL"
    watertight_mesh.export(str(upper_stl))

    files = repair_stl.discover_stl_files(str(tmp_path))
    assert len(files) == 1
    assert files[0].endswith(".STL")


def test_discover_ignores_non_stl_files(tmp_path, watertight_mesh):
    """Ignores non-.stl files."""
    # Create STL file
    stl_file = tmp_path / "test.stl"
    watertight_mesh.export(str(stl_file))

    # Create non-STL files
    (tmp_path / "readme.txt").write_text("test")
    (tmp_path / "data.obj").write_text("test")

    files = repair_stl.discover_stl_files(str(tmp_path))
    assert len(files) == 1
    assert files[0].endswith(".stl")
