#!/bin/sh
# Repair STL batch script (POSIX shell version)
# Source of truth: repair-stl.ps1

# Parse optional --help argument
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  cat <<'EOF'
Usage: repair-stl.sh [--engine local|windows] [--check-watertight [file.stl]]

Batch repair non-watertight STL files for 3D printing.

Recursively finds .stl files in the current directory, checks watertightness,
backs up originals to stl_backup/, and repairs them in-place.

Options:
  --engine local|windows          Select repair engine (default: local)
  --check-watertight [file.stl]   Check if file(s) are watertight (prints True/False)
                                  If no file is specified, checks all .stl files in CWD
  -h, --help                      Show this help message

Engines:
  local    Uses pymeshfix (if installed) with trimesh fallback. Cross-platform.
  windows  Uses Windows Printing3D RepairAsync API (Windows 10+ only).

Prerequisites:
  Python 3, trimesh, numpy
  Optional: pymeshfix (better local repair quality)
  Optional: winrt-Windows.Graphics.Printing3D (for Windows engine)
EOF
  exit 0
fi

# Directory of this script
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# Path to Python repair script
REPAIR_SCRIPT="$SCRIPT_DIR/repair_stl.py"

# Parse optional --check-watertight argument
if [ "$1" = "--check-watertight" ]; then
  if [ -n "$2" ]; then
    python "$REPAIR_SCRIPT" --check-watertight "$2"
  else
    python "$REPAIR_SCRIPT" --check-watertight
  fi
  exit $?
fi

# Parse optional --engine argument
ENGINE_ARG=""
if [ "$1" = "--engine" ]; then
  if [ -z "$2" ]; then
    printf "Error: --engine requires a value (local or windows)\n" >&2
    exit 1
  fi
  if [ "$2" != "local" ] && [ "$2" != "windows" ]; then
    printf "Error: --engine must be 'local' or 'windows', got '%s'\n" "$2" >&2
    exit 1
  fi
  ENGINE_ARG="--engine $2"
  shift 2
fi

# Delegate to Python batch mode
python "$REPAIR_SCRIPT" --batch $ENGINE_ARG
exit $?
