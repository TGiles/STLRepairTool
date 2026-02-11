import sys
import os
import trimesh
import numpy as np
import tempfile
import asyncio

# Optional: import pymeshfix if available
try:
    import pymeshfix

    HAS_PYMESHFIX = True
except ImportError:
    HAS_PYMESHFIX = False

# Optional: import Windows RepairAsync API
HAS_WINDOWS_API = False
try:
    from winrt.windows.graphics.printing3d import Printing3D3MFPackage
    from winrt.windows.storage import StorageFile, FileAccessMode

    HAS_WINDOWS_API = True
except ImportError as e:
    _winrt_import_error = e

# --- Handle command-line args ---
check_only = False
engine = "local"  # default engine

args = sys.argv[1:]
if "--check-watertight" in args:
    check_only = True
    idx = args.index("--check-watertight")
    args.pop(idx)
    if args:
        input_file = args[0]
    else:
        import glob
        stl_files = sorted(glob.glob("*.stl"))
        if not stl_files:
            print("No .stl files found in the current directory.")
            sys.exit(1)
        for stl_file in stl_files:
            mesh = trimesh.load(stl_file, force="mesh")
            print(f"{stl_file}: {mesh.is_watertight}")
        sys.exit(0)
    output_file = None
elif "--engine" in args:
    idx = args.index("--engine")
    args.pop(idx)
    engine = args.pop(idx)
    if engine not in ["local", "windows"]:
        print(f"Error: Unknown engine '{engine}'. Valid options: local, windows")
        sys.exit(1)
    input_file = args[0]
    output_file = args[1] if len(args) > 1 else args[0]
else:
    input_file = args[0] if len(args) > 0 else None
    output_file = args[1] if len(args) > 1 else input_file

if not input_file:
    print("Usage: repair_stl.py [--engine local|windows] [--check-watertight [file.stl]] input.stl [output.stl]")
    sys.exit(1)

# --- Load mesh ---
mesh = trimesh.load(input_file, force="mesh")

if check_only:
    print(mesh.is_watertight)
    sys.exit(0)


# --- Repair mesh ---
def repair_mesh(mesh):
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
        print(f"Error: Windows API not available: {_winrt_import_error}")
        print("Install required packages:")
        print("  pip install winrt-Windows.Graphics.Printing3D winrt-Windows.Storage")
        print("  pip install winrt-Windows.Storage.Streams winrt-Windows.Foundation")
        sys.exit(1)

    if sys.platform != "win32":
        print("Error: Windows API is only available on Windows.")
        print("Use --engine local for cross-platform repair.")
        sys.exit(1)

    # Check for lxml dependency (required for 3MF export)
    try:
        import lxml
    except ImportError:
        print("Error: lxml is required for 3MF export but not installed.")
        print("Install with: pip install lxml")
        sys.exit(1)

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


# --- Select repair engine ---
if engine == "windows":
    mesh = repair_mesh_windows(mesh, input_file, output_file)
else:
    mesh = repair_mesh(mesh)

# --- Save mesh ---
mesh.export(output_file)
file_size = os.path.getsize(output_file)
print(f"Saved repaired STL ({file_size:,} bytes) to {output_file}")
