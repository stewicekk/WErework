[CmdletBinding()]
param(
    [string]$Root = (Get-Location).Path
)
$ErrorActionPreference = 'Stop'
Set-Location $Root

$required = @(
  'AGENTS.md',
  'opencode.jsonc',
  '.opencode/agents/orchestrator.md',
  'docs/ORCHESTRATION.md',
  'docs/COMPATIBILITY_MATRIX.md',
  'docs/UI_SPEC.md',
  'docs/QA_GATES.md'
)

$missing = @($required | Where-Object { -not (Test-Path $_) })
if ($missing.Count -gt 0) {
    Write-Error ("Missing orchestrator files:`n" + ($missing -join "`n"))
}

$bad = @()
Get-ChildItem .opencode/skills -Recurse -Filter SKILL.md | ForEach-Object {
    $txt = Get-Content $_.FullName -Raw
    if ($txt -notmatch '(?m)^name:\s*[a-z0-9]+(?:-[a-z0-9]+)*\s*$') { $bad += $_.FullName }
    if ($txt -notmatch '(?m)^description:\s*.+$') { $bad += $_.FullName }
}
if ($bad.Count -gt 0) {
    Write-Error ("Invalid skill frontmatter in:`n" + ($bad -join "`n"))
}

Write-Host 'OpenCode orchestrator structure: OK'
