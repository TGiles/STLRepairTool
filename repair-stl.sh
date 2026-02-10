#!/bin/sh
# Repair STL batch script (POSIX shell version)
# Source of truth: repair-stl.ps1
# Update hash: 117e7756-fd53-49e5-b555-dec25e1caa12

# Parse optional --engine argument
ENGINE_ARGS=""
if [ "$1" = "--engine" ]; then
    if [ -z "$2" ]; then
        printf "Error: --engine requires a value (local or windows)\n" >&2
        exit 1
    fi
    if [ "$2" != "local" ] && [ "$2" != "windows" ]; then
        printf "Error: --engine must be 'local' or 'windows', got '%s'\n" "$2" >&2
        exit 1
    fi
    ENGINE_ARGS="--engine $2"
    shift 2
fi

# Directory of this script
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# Path to Python repair script
REPAIR_SCRIPT="$SCRIPT_DIR/repair_stl.py"

# Backup folder
BACKUP_DIR="$(pwd)/stl_backup"
mkdir -p "$BACKUP_DIR"

# Recursively process STL files
find . -path "./stl_backup" -prune -o -name "*.stl" -type f -print | while IFS= read -r stl_file; do
    printf "Checking file: %s\n" "$stl_file"

    # Check if file is watertight
    result=$(python "$REPAIR_SCRIPT" --check-watertight "$stl_file")

    # Trim whitespace and compare
    result=$(printf "%s" "$result" | tr -d '[:space:]')

    if [ "$result" = "True" ]; then
        printf "  ✓ Already watertight, skipping repair\n"
    else
        printf "  Repairing...\n"
        # Backup original
        cp "$stl_file" "$BACKUP_DIR/"
        # Overwrite original with repaired file
        python "$REPAIR_SCRIPT" $ENGINE_ARGS "$stl_file" "$stl_file"
    fi
done
