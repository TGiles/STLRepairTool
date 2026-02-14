import sys
import os
import trimesh
import numpy as np
import tempfile
import asyncio
import argparse
import glob
import time
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

__version__ = "1.0.0"

# Optional: import pymeshfix if available
try:
    import pymeshfix
    HAS_PYMESHFIX = True
except ImportError:
    HAS_PYMESHFIX = False

# Optional: import Windows RepairAsync API
HAS_WINDOWS_API = False
_winrt_import_error = None
try:
    from winrt.windows.graphics.printing3d import Printing3D3MFPackage
    from winrt.windows.storage import StorageFile, FileAccessMode
    HAS_WINDOWS_API = True
except ImportError as e:
    _winrt_import_error = e


# --- Result types ---

class FileStatus(Enum):
    REPAIRED = "repaired"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class RepairResult:
    file_path: str
    status: FileStatus
    output_size: int = 0
    error_message: str = ""
    elapsed_seconds: float = 0.0


# --- Repair functions (module scope for pickling) ---

def repair_mesh(mesh):
    """Repair mesh using local engines (pymeshfix or trimesh fallback)."""
    pymeshfix_ok = False

    if HAS_PYMESHFIX:
        try:
            meshfix = pymeshfix.MeshFix(mesh.vertices, mesh.faces)
            meshfix.repair()
            repaired = meshfix.mesh
            vertices = np.asarray(repaired.points)
            faces = np.asarray(repaired.faces)
            if faces.ndim == 1:
                # VTK format: [3, v0, v1, v2, 3, v3, v4, v5, ...]
                # Strip the leading vertex-count from each face
                faces = faces.reshape(-1, 4)[:, 1:]
            mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
            pymeshfix_ok = True
        except Exception as e:
            print(f"Warning: pymeshfix repair failed: {e}")

    if not pymeshfix_ok:
        # Trimesh-only fallback
        try:
            mesh.merge_vertices()
            mesh.fill_holes()
            mesh.remove_duplicate_faces()
            mesh.remove_unreferenced_vertices()
            mesh.fix_normals()
        except Exception as e:
            print(f"Warning: trimesh fallback repair failed: {e}")

    return mesh


async def repair_mesh_windows_async(input_3mf_path, output_3mf_path):
    """Call Windows RepairAsync API on a 3MF file."""
    # Convert to absolute Windows path
    input_3mf_path = os.path.abspath(input_3mf_path)
    output_3mf_path = os.path.abspath(output_3mf_path)

    # Load input 3MF
    storage_file = await StorageFile.get_file_from_path_async(input_3mf_path)
    stream = await storage_file.open_async(FileAccessMode.READ)

    # Create package and load model
    package = Printing3D3MFPackage()
    model = await package.load_model_from_package_async(stream)
    stream.close()

    # Repair the model
    await model.repair_async()

    # Save repaired model back into the SAME package (no need for output_package)
    await package.save_model_to_package_async(model)

    # Get serialized 3MF data as a stream
    saved_stream = await package.save_async()

    # Read bytes from the WinRT stream and write to file
    saved_stream.seek(0)
    from winrt.windows.storage.streams import DataReader
    reader = DataReader(saved_stream)
    await reader.load_async(saved_stream.size)
    buffer = reader.read_buffer(saved_stream.size)
    reader.close()
    saved_stream.close()

    with open(output_3mf_path, 'wb') as f:
        f.write(bytes(buffer))


def repair_mesh_windows(mesh, input_file, output_file):
    """Repair mesh using Windows RepairAsync API via 3MF conversion."""
    if not HAS_WINDOWS_API:
        raise RuntimeError(
            f"Windows API not available: {_winrt_import_error}\n"
            "Install required packages:\n"
            "  pip install winrt-Windows.Graphics.Printing3D winrt-Windows.Storage\n"
            "  pip install winrt-Windows.Storage.Streams winrt-Windows.Foundation"
        )

    if sys.platform != "win32":
        raise RuntimeError(
            "Windows API is only available on Windows.\n"
            "Use --engine local for cross-platform repair."
        )

    # Check for lxml dependency (required for 3MF export)
    try:
        import lxml
    except ImportError:
        raise RuntimeError(
            "lxml is required for 3MF export but not installed.\n"
            "Install with: pip install lxml"
        )

    input_3mf_path = None
    output_3mf_path = None

    try:
        # Create temporary 3MF files
        temp_input_3mf = tempfile.NamedTemporaryFile(
            suffix=".3mf", delete=False, mode="wb"
        )
        temp_output_3mf = tempfile.NamedTemporaryFile(
            suffix=".3mf", delete=False, mode="wb"
        )

        input_3mf_path = temp_input_3mf.name
        output_3mf_path = temp_output_3mf.name

        temp_input_3mf.close()
        temp_output_3mf.close()

        # Export mesh to 3MF
        mesh.export(input_3mf_path)

        # Call Windows API
        try:
            asyncio.run(repair_mesh_windows_async(input_3mf_path, output_3mf_path))
        except Exception as e:
            print(f"Warning: Windows RepairAsync failed: {e}")
            print("Falling back to local repair...")
            return repair_mesh(mesh)

        # Load repaired mesh from 3MF
        # process=True is required to merge duplicate vertices from 3MF format
        # (3MF stores vertices per-triangle; without merging, mesh is "triangle soup" and never watertight)
        repaired_mesh = trimesh.load(output_3mf_path, force="mesh", process=True)

        # Validate watertight after proper vertex merging
        if not repaired_mesh.is_watertight:
            print("Warning: Windows RepairAsync output is not watertight after processing.")
            print("Falling back to local repair...")
            return repair_mesh(mesh)

        return repaired_mesh

    finally:
        # Clean up temp files
        if input_3mf_path and os.path.exists(input_3mf_path):
            try:
                os.unlink(input_3mf_path)
            except Exception:
                pass
        if output_3mf_path and os.path.exists(output_3mf_path):
            try:
                os.unlink(output_3mf_path)
            except Exception:
                pass


# --- Single-file operations ---

def check_watertight(file_path):
    """Check if a single STL file is watertight."""
    mesh = trimesh.load(file_path, force="mesh")
    return mesh.is_watertight


def repair_single_file(input_file, output_file, engine):
    """Repair a single STL file. Returns RepairResult."""
    temp_output_path = None
    start_time = time.time()

    try:
        # Load mesh
        mesh = trimesh.load(input_file, force="mesh")

        # Select repair engine
        if engine == "windows":
            mesh = repair_mesh_windows(mesh, input_file, output_file)
        else:
            mesh = repair_mesh(mesh)

        # Save mesh with atomic write
        output_dir = os.path.dirname(os.path.abspath(output_file)) or "."
        temp_fd = tempfile.NamedTemporaryFile(suffix=".stl.tmp", dir=output_dir, delete=False)
        temp_output_path = temp_fd.name
        temp_fd.close()

        mesh.export(temp_output_path, file_type='stl')
        os.replace(temp_output_path, output_file)  # atomic on NTFS and POSIX
        temp_output_path = None  # no cleanup needed after successful replace

        file_size = os.path.getsize(output_file)
        elapsed = time.time() - start_time

        return RepairResult(
            file_path=input_file,
            status=FileStatus.REPAIRED,
            output_size=file_size,
            elapsed_seconds=elapsed
        )

    except KeyboardInterrupt:
        # Clean up temp file if it exists
        if temp_output_path and os.path.exists(temp_output_path):
            try:
                os.unlink(temp_output_path)
            except Exception:
                pass
        raise

    except Exception as e:
        elapsed = time.time() - start_time
        if temp_output_path and os.path.exists(temp_output_path):
            try:
                os.unlink(temp_output_path)
            except Exception:
                pass
        return RepairResult(
            file_path=input_file,
            status=FileStatus.FAILED,
            error_message=str(e),
            elapsed_seconds=elapsed
        )


# --- Batch mode ---

def discover_stl_files(root_dir="."):
    """Recursively discover all .stl files, excluding stl_backup/ directory."""
    stl_files = []
    root_path = Path(root_dir).resolve()

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Exclude stl_backup directory
        dirnames[:] = [d for d in dirnames if d != "stl_backup"]

        for filename in filenames:
            if filename.lower().endswith(".stl"):
                stl_files.append(os.path.join(dirpath, filename))

    return sorted(stl_files)


def _worker_repair_file(file_path, engine, backup_dir, root_dir):
    """
    Worker function for batch repair. Runs in subprocess.
    Returns RepairResult, never prints (except warnings), never calls sys.exit().
    """
    start_time = time.time()

    try:
        # Load mesh and check watertightness
        mesh = trimesh.load(file_path, force="mesh")
        if mesh.is_watertight:
            elapsed = time.time() - start_time
            return RepairResult(
                file_path=file_path,
                status=FileStatus.SKIPPED,
                elapsed_seconds=elapsed
            )

        # Backup original file (preserve relative path structure)
        if backup_dir:
            rel_path = os.path.relpath(file_path, root_dir)
            backup_path = os.path.join(backup_dir, rel_path)
            backup_parent = os.path.dirname(backup_path)
            os.makedirs(backup_parent, exist_ok=True)

            import shutil
            shutil.copy2(file_path, backup_path)

        # Repair using specified engine
        if engine == "windows":
            repaired_mesh = repair_mesh_windows(mesh, file_path, file_path)
        else:
            repaired_mesh = repair_mesh(mesh)

        # Save with atomic write
        output_dir = os.path.dirname(os.path.abspath(file_path)) or "."
        temp_fd = tempfile.NamedTemporaryFile(suffix=".stl.tmp", dir=output_dir, delete=False)
        temp_output_path = temp_fd.name
        temp_fd.close()

        repaired_mesh.export(temp_output_path, file_type='stl')
        os.replace(temp_output_path, file_path)

        file_size = os.path.getsize(file_path)
        elapsed = time.time() - start_time

        return RepairResult(
            file_path=file_path,
            status=FileStatus.REPAIRED,
            output_size=file_size,
            elapsed_seconds=elapsed
        )

    except Exception as e:
        elapsed = time.time() - start_time
        return RepairResult(
            file_path=file_path,
            status=FileStatus.FAILED,
            error_message=str(e),
            elapsed_seconds=elapsed
        )


def batch_repair(root_dir=".", engine="local", workers=None, backup=True):
    """
    Batch repair all STL files in root_dir using parallel processing.
    Returns list of RepairResult.
    """
    # Discover files
    stl_files = discover_stl_files(root_dir)

    if not stl_files:
        print("No .stl files found in the current directory.")
        return []

    # Default workers: min(cpu_count, 8)
    if workers is None:
        workers = min(os.cpu_count() or 1, 8)

    # Validate engine early (before spawning workers)
    if engine == "windows":
        if not HAS_WINDOWS_API:
            print(f"Error: Windows API not available: {_winrt_import_error}")
            print("Install required packages:")
            print("  pip install winrt-Windows.Graphics.Printing3D winrt-Windows.Storage")
            print("  pip install winrt-Windows.Storage.Streams winrt-Windows.Foundation")
            sys.exit(1)
        if sys.platform != "win32":
            print("Error: Windows API is only available on Windows.")
            print("Use --engine local for cross-platform repair.")
            sys.exit(1)
        try:
            import lxml
        except ImportError:
            print("Error: lxml is required for 3MF export but not installed.")
            print("Install with: pip install lxml")
            sys.exit(1)

    # Setup backup directory
    backup_dir = None
    if backup:
        backup_dir = os.path.join(root_dir, "stl_backup")
        os.makedirs(backup_dir, exist_ok=True)

    print(f"Found {len(stl_files)} STL file(s). Repairing with {workers} worker(s)...")
    print()

    results = []
    completed_count = 0
    total_count = len(stl_files)
    batch_start_time = time.time()

    try:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(_worker_repair_file, file_path, engine, backup_dir, root_dir): file_path
                for file_path in stl_files
            }

            # Collect results as they complete
            for future in as_completed(future_to_file):
                result = future.result()
                results.append(result)
                completed_count += 1

                # Print per-file result
                rel_path = os.path.relpath(result.file_path, root_dir)
                if result.status == FileStatus.REPAIRED:
                    print(f"[{completed_count}/{total_count}] {rel_path} -- REPAIRED ({result.output_size:,} bytes) [{result.elapsed_seconds:.1f}s]")
                elif result.status == FileStatus.SKIPPED:
                    print(f"[{completed_count}/{total_count}] {rel_path} -- SKIPPED (already watertight) [{result.elapsed_seconds:.1f}s]")
                elif result.status == FileStatus.FAILED:
                    print(f"[{completed_count}/{total_count}] {rel_path} -- FAILED: {result.error_message} [{result.elapsed_seconds:.1f}s]")

    except KeyboardInterrupt:
        print("\n\nInterrupted! Cancelling remaining tasks...")
        # Print partial summary
        _print_batch_summary(results, time.time() - batch_start_time, interrupted=True)
        sys.exit(130)

    # Print final summary
    print()
    _print_batch_summary(results, time.time() - batch_start_time, interrupted=False)

    return results


def _print_batch_summary(results, total_time, interrupted=False):
    """Print batch repair summary."""
    repaired = [r for r in results if r.status == FileStatus.REPAIRED]
    skipped = [r for r in results if r.status == FileStatus.SKIPPED]
    failed = [r for r in results if r.status == FileStatus.FAILED]

    print("===== Batch Repair Summary =====")
    if interrupted:
        print(f"  Status:        INTERRUPTED")
    print(f"  Total files:   {len(results)}")
    print(f"  Repaired:      {len(repaired)}")
    print(f"  Skipped:       {len(skipped)} (already watertight)")
    print(f"  Failed:        {len(failed)}")
    print(f"  Total time:    {total_time:.1f}s")

    if failed:
        print()
        print("  Failed files:")
        for r in failed:
            print(f"    {r.file_path}: {r.error_message}")


# --- CLI Entry Point ---

def main():
    parser = argparse.ArgumentParser(
        description="Repair STL files using various engines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python repair_stl.py input.stl                    # repair single file (in-place)
  python repair_stl.py input.stl output.stl         # repair single file (to output)
  python repair_stl.py --engine windows input.stl   # use Windows repair engine
  python repair_stl.py --check-watertight file.stl  # check if file is watertight
  python repair_stl.py --check-watertight           # check all .stl files in CWD
  python repair_stl.py --batch                      # repair all files in CWD (parallel)
  python repair_stl.py --batch --workers 4          # use 4 worker processes
  python repair_stl.py --batch --engine windows     # batch with Windows engine
  python repair_stl.py --batch --no-backup          # skip backup creation
        """
    )

    parser.add_argument("input_file", nargs="?", help="Input STL file (for single-file mode)")
    parser.add_argument("output_file", nargs="?", help="Output STL file (defaults to input_file)")
    parser.add_argument("--engine", choices=["local", "windows"], default="local",
                        help="Repair engine to use (default: local)")
    parser.add_argument("--check-watertight", action="store_true",
                        help="Check if file(s) are watertight without repairing")
    parser.add_argument("--batch", action="store_true",
                        help="Batch mode: repair all .stl files in current directory")
    parser.add_argument("--workers", type=int, default=None,
                        help="Number of worker processes for batch mode (default: min(cpu_count, 8))")
    parser.add_argument("--no-backup", action="store_true",
                        help="Skip creating backups in batch mode")

    args = parser.parse_args()

    # --- Check-watertight mode ---
    if args.check_watertight:
        if args.input_file:
            result = check_watertight(args.input_file)
            print(result)
        else:
            stl_files = discover_stl_files(".")
            if not stl_files:
                print("No .stl files found in the current directory.")
                sys.exit(1)
            for stl_file in stl_files:
                is_watertight = check_watertight(stl_file)
                print(f"{stl_file}: {is_watertight}")
        sys.exit(0)

    # --- Batch mode ---
    if args.batch:
        batch_repair(
            root_dir=".",
            engine=args.engine,
            workers=args.workers,
            backup=not args.no_backup
        )
        sys.exit(0)

    # --- Single-file mode ---
    if not args.input_file:
        parser.print_help()
        sys.exit(1)

    output_file = args.output_file or args.input_file

    try:
        result = repair_single_file(args.input_file, output_file, args.engine)

        if result.status == FileStatus.REPAIRED:
            print(f"Saved repaired STL ({result.output_size:,} bytes) to {output_file}")
            sys.exit(0)
        elif result.status == FileStatus.FAILED:
            print(f"Error: {result.error_message}", file=sys.stderr)
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nInterrupted. Original file unchanged.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
