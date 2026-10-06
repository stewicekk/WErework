[CmdletBinding()]
param(
    [string]$Root = (Get-Location).Path
)

$ErrorActionPreference = 'Stop'
Set-Location $Root

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$out = Join-Path $Root "docs/baseline/$stamp"
New-Item -ItemType Directory -Force -Path $out | Out-Null

"# Repository tree" | Set-Content (Join-Path $out 'tree.md')
Get-ChildItem -Recurse -File | Where-Object { $_.FullName -notmatch '\\(\.git|build|out|bin|obj|_backup|_export)\\' } |
    Sort-Object FullName |
    ForEach-Object { $_.FullName.Substring($Root.Length).TrimStart('\') } |
    Add-Content (Join-Path $out 'tree.md')

"# C++/build inventory" | Set-Content (Join-Path $out 'sources.md')
Get-ChildItem -Recurse -File -Include *.cpp,*.h,*.hpp,*.rc,*.vcxproj,*.filters,*.sln,*.props,*.targets,*.py,*.txt,*.ini,*.json |
    Sort-Object FullName |
    Select-Object FullName,Length,LastWriteTime |
    Format-Table -AutoSize | Out-String -Width 240 |
    Add-Content (Join-Path $out 'sources.md')

"# Git state" | Set-Content (Join-Path $out 'git.md')
try { git status --short | Add-Content (Join-Path $out 'git.md') } catch { "git unavailable: $($_.Exception.Message)" | Add-Content (Join-Path $out 'git.md') }
try { git branch --show-current | Add-Content (Join-Path $out 'git.md') } catch {}
try { git log -10 --oneline | Add-Content (Join-Path $out 'git.md') } catch {}

"# Toolchain" | Set-Content (Join-Path $out 'toolchain.md')
foreach ($cmd in @('cl','cmake','msbuild','ninja','python','where')) {
    try {
        "## $cmd" | Add-Content (Join-Path $out 'toolchain.md')
        & $cmd --version 2>&1 | Select-Object -First 8 | Add-Content (Join-Path $out 'toolchain.md')
    } catch { "not found" | Add-Content (Join-Path $out 'toolchain.md') }
}

$patterns = @('WorldEditor','WORLD_EDITOR','TerrainLib','PRTerrainlib','Granny','DevIL','SpeedTree','EterLib','GameLib','pack/Index','ymir work')
"# Keyword scan" | Set-Content (Join-Path $out 'keywords.md')
foreach ($p in $patterns) {
    "## $p" | Add-Content (Join-Path $out 'keywords.md')
    Get-ChildItem -Recurse -File -Include *.cpp,*.h,*.hpp,*.vcxproj,*.props,*.targets,*.txt,*.ini,*.py |
        Select-String -SimpleMatch $p -ErrorAction SilentlyContinue |
        Select-Object -First 120 Path,LineNumber,Line |
        Format-Table -AutoSize | Out-String -Width 260 |
        Add-Content (Join-Path $out 'keywords.md')
}

Write-Host "Baseline audit written to $out"
