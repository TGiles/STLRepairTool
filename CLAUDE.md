# STL Repair Tool Project Configuration

## PowerShell

Primary language: Python. This project also uses PowerShell (.ps1) and Shell (.sh) wrapper scripts. When adding CLI flags to PowerShell scripts, use proper PowerShell parameter syntax (e.g., `-Help` switch parameter) rather than GNU-style `--help` which PowerShell intercepts.

When editing PowerShell scripts, always check for UTF-8 BOM encoding issues. If a script has smart quotes, checkmark characters, or other non-ASCII content, ensure the file is saved with UTF-8 BOM encoding. Use Python to write BOM if PowerShell methods fail due to file locking.

## Testing

When writing tests for this codebase, verify the exact data structures (class fields, return types) of the code under test before writing assertions. Read the source definitions first rather than assuming field names like RepairResult or FileStatus.
