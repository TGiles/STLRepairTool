# Repair STL batch script

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

.PARAMETER CheckWatertight
    Check if file(s) are watertight. Prints True or False and exits.
    If -File is provided, checks that file. Otherwise, checks all .stl files in CWD.

.PARAMETER File
    STL file to check (optional, used with -CheckWatertight).

.EXAMPLE
    repair-stl.ps1
    Repair all STL files using the default local engine.

.EXAMPLE
    repair-stl.ps1 -Engine windows
    Repair all STL files using the Windows RepairAsync engine.

.EXAMPLE
    repair-stl.ps1 -CheckWatertight -File model.stl
    Check if model.stl is watertight without repairing.

.EXAMPLE
    repair-stl.ps1 -CheckWatertight
    Check all .stl files in current directory for watertightness.

.NOTES
    Prerequisites: Python 3, trimesh, numpy
    Optional: pymeshfix (better local repair quality)
    Optional: winrt-Windows.Graphics.Printing3D (for Windows engine)
#>

param(
    [ValidateSet('local', 'windows')]
    [string]$Engine,

    [switch]$CheckWatertight,

    [string]$File,

    [Alias('h')]
    [switch]$Help
)

if ($Help) {
    Get-Help $MyInvocation.MyCommand.Path -Detailed
    exit
}

# Handle --check-watertight mode
if ($CheckWatertight) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $repairScript = Join-Path $scriptDir "repair_stl.py"
    if ($File) {
        & python "$repairScript" --check-watertight "$File"
    } else {
        & python "$repairScript" --check-watertight
    }
    exit $LASTEXITCODE
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
