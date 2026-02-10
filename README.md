# STL Repair Tool

Batch repair non-watertight STL files for 3D printing. This tool recursively finds `.stl` files in the current directory, checks watertightness, backs up originals, and repairs them in-place.

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
repair-stl.sh
```

**PowerShell:**
```powershell
repair-stl.ps1
```

### Single File via Python Directly

**Check watertightness:**
```bash
python repair_stl.py --check-watertight model.stl
```

**Repair in-place (default local engine):**
```bash
python repair_stl.py model.stl
```

**Repair to new file:**
```bash
python repair_stl.py input.stl output.stl
```

**Repair using Windows engine:**
```bash
python repair_stl.py --engine windows input.stl output.stl
```

**Repair using local engine (explicit):**
```bash
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
- Falls back to local engine if the Windows API fails
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
