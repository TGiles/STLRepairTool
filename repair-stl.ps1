# Repair STL batch script
# Update hash: f9e4b7d2-3a1c-4e82-bb5d-8c9f1a2d6e4f

# Directory of this script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Path to Python repair script
$repairScript = Join-Path $scriptDir "repair_stl.py"

# Backup folder
$backupDir = Join-Path (Get-Location) "stl_backup"
if (!(Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
}

# Recursively process STL files
Get-ChildItem -Path "." -Filter "*.stl" -Recurse | ForEach-Object {

    $stlFile = $_.FullName
    Write-Host "Checking file: $stlFile"

    # Use stop-parsing to safely pass filenames with special characters
    $result = & python "$repairScript" --check-watertight "$stlFile"
    $isWatertight = $result.Trim() -eq "True"

    if ($isWatertight) {
        Write-Host "  ✓ Already watertight, skipping repair"
    } else {
        Write-Host "  Repairing..."
        # Backup original
        Copy-Item -Path $stlFile -Destination $backupDir -Force
        # Overwrite original with repaired file
        & python "$repairScript" "$stlFile" "$stlFile"
    }

} # End of ForEach-Object
