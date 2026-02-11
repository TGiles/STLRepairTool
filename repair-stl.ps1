# Repair STL batch script
# Update hash: 117e7756-fd53-49e5-b555-dec25e1caa12

<#
.SYNOPSIS
    Batch repair non-watertight STL files for 3D printing.

.DESCRIPTION
    Recursively finds .stl files in the current directory, checks watertightness,
    backs up originals to stl_backup/, and repairs them in-place.

.PARAMETER Engine
    Select repair engine. Valid values: local, windows. Default: local.
    - local: Uses pymeshfix (if installed) with trimesh fallback. Cross-platform.
    - windows: Uses Windows Printing3D RepairAsync API (Windows 10+ only).

.EXAMPLE
    repair-stl.ps1
    Repair all STL files using the default local engine.

.EXAMPLE
    repair-stl.ps1 -Engine windows
    Repair all STL files using the Windows RepairAsync engine.

.NOTES
    Prerequisites: Python 3, trimesh, numpy
    Optional: pymeshfix (better local repair quality)
    Optional: winrt-Windows.Graphics.Printing3D (for Windows engine)
#>

param(
    [ValidateSet('local', 'windows')]
    [string]$Engine,

    [Alias('h')]
    [switch]$Help
)

if ($Help) {
    Get-Help $MyInvocation.MyCommand.Path -Detailed
    exit
}

# Directory of this script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Path to Python repair script
$repairScript = Join-Path $scriptDir "repair_stl.py"

# Build engine arguments if specified
$engineArgs = @()
if ($Engine) {
    $engineArgs = @("--engine", $Engine)
}

# Backup folder
$backupDir = Join-Path (Get-Location) "stl_backup"
if (!(Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
}

# Recursively process STL files
Get-ChildItem -Path "." -Filter "*.stl" -Recurse |
    Where-Object { $_.FullName -notlike "$backupDir\*" } |
    ForEach-Object {

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
        & python "$repairScript" @engineArgs "$stlFile" "$stlFile"
    }

} # End of ForEach-Object
