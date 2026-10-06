[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$TargetRepo,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$source = Split-Path -Parent $PSScriptRoot
$target = (Resolve-Path $TargetRepo).Path

if (-not (Test-Path (Join-Path $target '.git'))) {
    throw "TargetRepo is not a Git worktree: $target"
}

$items = @('AGENTS.md','opencode.jsonc','.opencode','docs','research','scripts')
foreach ($item in $items) {
    $src = Join-Path $source $item
    $dst = Join-Path $target $item
    if ((Test-Path $dst) -and -not $Force) {
        throw "Target already contains '$item'. Re-run with -Force only after inspecting the existing files."
    }
    Copy-Item -Recurse -Force $src $dst
}

Write-Host "Installed orchestrator into $target"
Write-Host "Next: powershell -ExecutionPolicy Bypass -File .\scripts\audit.ps1"
