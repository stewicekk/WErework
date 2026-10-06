[CmdletBinding()]
param(
    [string]$Root = (Get-Location).Path
)

$ErrorActionPreference = 'Stop'
Set-Location $Root

if (-not (Test-Path 'src/newschool/__init__.py')) {
    throw "Run from the WErework root (src/newschool missing): $Root"
}

$env:PYTHONPATH = (Join-Path $Root 'src')
& python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) {
    throw "newschool core tests FAILED (exit $LASTEXITCODE)"
}
Write-Host 'newschool core tests: ALL GREEN'
