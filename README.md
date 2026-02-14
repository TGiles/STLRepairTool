# STL Repair Tool

Batch repair non-watertight STL files for 3D printing. This tool recursively finds `.stl` files in the current directory, checks watertightness, backs up originals, and repairs them in-place.

**NOTE:** I used Claude Code for this project.
I am not a expert Python programmer nor do I know the inner details of `pymeshfix`, `trimesh`, or the Windows `Printing3D.RepairAsync()` API.
While there are reasonable precautions, such as creating a backup folder before performing any repairs, **you** are responsible for how you use this tool.

I'd recommend checking a known non-manifold STL and then checking the results in your favorite slicer.
## How It Works

- Checks each STL for watertightness using `trimesh`
- Already-watertight files are skipped
- Non-watertight files are backed up to `stl_backup/` in the current directory, then repaired in-place
- Two repair engines available:
  - **Local** (default): Uses `pymeshfix` (if installed) with `trimesh` as fallback
  - **Windows**: Uses Windows `Printing3D.RepairAsync()` API (Windows 10+ only)
- Local repair operations include:
  - Fill holes
  - Remove duplicate faces
  - Remove unreferenced vertices
  - Fix normals
  - Merge vertices

## Features

- **Parallel Batch Processing**: Repairs multiple files concurrently using process pools for faster throughput
- **Progress Tracking**: Real-time progress with file-by-file status updates and timing information
- **Graceful Interruption**: Handles Ctrl+C cleanly with partial summary reporting
- **Configurable Workers**: Control parallelism with `--workers` flag (defaults to min(cpu_count, 8))
- **Flexible Watertight Checking**: Check single files or all STLs in a directory for watertightness
- **Automatic Fallback**: Windows engine automatically falls back to local repair if the API fails or output isn't watertight
- **Optional Backups**: Skip backup creation in batch mode with `--no-backup` flag
- **Atomic Writes**: Uses temporary files and atomic replacement to prevent partial/corrupted output
- **Comprehensive Test Suite**: Full pytest coverage for reliability

## Prerequisites

### Core Dependencies (Required)

- Python 3
- `trimesh` (required)
- `numpy` (required)

```bash
pip install trimesh numpy
```

### Optional Dependencies

**For better local repair quality:**
```bash
pip install pymeshfix
```

**For Windows RepairAsync engine (Windows 10+ only):**
```bash
pip install winrt-Windows.Graphics.Printing3D winrt-Windows.Storage winrt-Windows.Storage.Streams winrt-Windows.Foundation
```

**Note:** The Windows engine uses the `Windows.Graphics.Printing3D.Printing3DModel.RepairAsync()` API, which was previously cloud-based but now runs locally. Results may vary depending on mesh complexity and Windows version.

## Usage

### Batch Mode (Recommended)

Run the wrapper script from any directory containing STL files:

**Bash/Git Bash:**
```bash
# Repair all STL files (default local engine)
repair-stl.sh

# Repair all STL files with Windows engine
repair-stl.sh --engine windows

# Check if a single file is watertight
repair-stl.sh --check-watertight model.stl

# Check all STL files in current directory for watertightness
repair-stl.sh --check-watertight
```

**PowerShell:**
```powershell
# Repair all STL files (default local engine)
repair-stl.ps1

# Repair all STL files with Windows engine
repair-stl.ps1 -Engine windows

# Check if a single file is watertight
repair-stl.ps1 -CheckWatertight -File model.stl

# Check all STL files in current directory for watertightness
repair-stl.ps1 -CheckWatertight
```

### Python Direct Usage

**Batch mode (parallel processing):**
```bash
# Repair all .stl files in current directory (parallel)
python repair_stl.py --batch

# Use specific number of worker processes
python repair_stl.py --batch --workers 4

# Batch repair with Windows engine
python repair_stl.py --batch --engine windows

# Skip backup creation
python repair_stl.py --batch --no-backup
```

**Check watertightness:**
```bash
# Check a single file
python repair_stl.py --check-watertight model.stl

# Check all .stl files in current directory
python repair_stl.py --check-watertight
```

**Single file repair:**
```bash
# Repair in-place (default local engine)
python repair_stl.py model.stl

# Repair to new file
python repair_stl.py input.stl output.stl

# Repair using Windows engine
python repair_stl.py --engine windows input.stl output.stl

# Repair using local engine (explicit)
python repair_stl.py --engine local input.stl output.stl
```

## Repair Engines

### Local Engine (Default)

The local engine uses:
1. `pymeshfix` if installed (recommended for best quality)
2. `trimesh` built-in repair as fallback

This engine works on all platforms (Windows, macOS, Linux).

### Windows Engine

The Windows engine uses the `Windows.Graphics.Printing3D.Printing3DModel.RepairAsync()` API. This is the same repair method used by PrusaSlicer and Windows 3D Builder.

**Requirements:**
- Windows 10 or later
- PyWinRT packages (see Prerequisites)

**How it works:**
1. Converts STL → 3MF
2. Calls `RepairAsync()` on the 3MF model
3. Converts repaired 3MF → STL

**Notes:**
- The Windows API was previously cloud-based but now runs locally
- Repair quality and reliability may vary
- Automatically validates watertightness after repair and falls back to local engine if output is not watertight
- Falls back to local engine if the Windows API fails or encounters errors
- Only available on Windows systems

**When to use:**
- For meshes that local repair struggles with
- When you want the same repair behavior as PrusaSlicer/3D Builder
- For comparison with local repair results

## Adding to PATH

To run the tool from any directory, add the STL Repair Tool directory to your PATH:

### Bash

Add this line to `~/.bashrc`:
```bash
export PATH="$PATH:/path/to/STLRepairTool"
```

### PowerShell

Add this line to your PowerShell profile (`$PROFILE`):
```powershell
$env:PATH += ";C:\path\to\STLRepairTool"
```

**Note:** Restart your terminal after editing the configuration file.

## Project Structure

- `repair_stl.py` — Core Python repair logic
- `repair-stl.sh` — POSIX shell wrapper for batch processing
- `repair-stl.ps1` — PowerShell wrapper for batch processing

## Notes & Tips

- The backup directory (`stl_backup/`) is created in the working directory, not the script directory
- Files with special characters in names are handled safely
- The script processes subdirectories recursively
- Original files are preserved in backups before any repairs are attempted
- Batch mode uses parallel processing by default for faster repairs on multi-core systems
- Keyboard interrupts (Ctrl+C) are handled gracefully with cleanup and partial summaries

## Testing

The tool includes a comprehensive pytest test suite covering:

- Single file repair operations
- Batch processing with parallel workers
- Watertight checking functionality
- Both local and Windows repair engines
- Error handling and edge cases
- Command-line interface and subprocess execution

Run tests with:
```bash
pytest test_repair_stl.py -v
```
