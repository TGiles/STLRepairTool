# Repair STL batch script
# Update hash: 117e7756-fd53-49e5-b555-dec25e1caa12

param(
    [ValidateSet('local', 'windows')]
    [string]$Engine
)

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
