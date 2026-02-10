#!/bin/sh
# Repair STL batch script (POSIX shell version)
# Source of truth: repair-stl.ps1
# Update hash: f9e4b7d2-3a1c-4e82-bb5d-8c9f1a2d6e4f

# Directory of this script
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# Path to Python repair script
REPAIR_SCRIPT="$SCRIPT_DIR/repair_stl.py"

# Backup folder
BACKUP_DIR="$(pwd)/stl_backup"
mkdir -p "$BACKUP_DIR"

# Recursively process STL files
find . -name "*.stl" -type f | while IFS= read -r stl_file; do
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
        python "$REPAIR_SCRIPT" "$stl_file" "$stl_file"
    fi
done
