<#
.SYNOPSIS
    Bootstrap Claude Code skills from this repo onto the current machine.

.DESCRIPTION
    Creates directory junctions from %USERPROFILE%\.claude\skills\<name> to each
    top-level skill folder in this repository. A "skill folder" is any directory
    at the repo root that contains a SKILL.md file.

    Idempotent: running it multiple times is safe.
      - Missing junction -> created.
      - Junction already pointing to the correct folder -> left alone.
      - Junction pointing somewhere else -> replaced.
      - A real directory (not a junction) sitting at the link path -> warned and
        left untouched so user data is never destroyed.

.USAGE
    From this repo's root:
        .\bootstrap.ps1

    If PowerShell's execution policy blocks it:
        powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1

    Run once per machine after cloning. Re-run after any `git pull` that adds
    or renames skill folders.
#>

$ErrorActionPreference = "Stop"

$repoRoot  = $PSScriptRoot
$skillsDir = Join-Path $env:USERPROFILE ".claude\skills"

New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null

$created = 0
$skipped = 0
$retargeted = 0
$conflicts = 0

$skills = Get-ChildItem -Path $repoRoot -Directory | Where-Object {
    Test-Path -LiteralPath (Join-Path $_.FullName "SKILL.md")
}

if (-not $skills) {
    Write-Host "No skill folders (directories containing SKILL.md) found under $repoRoot." -ForegroundColor Yellow
    return
}

Write-Host "Bootstrapping skills from $repoRoot into $skillsDir" -ForegroundColor Cyan
Write-Host ""

foreach ($skill in $skills) {
    $name   = $skill.Name
    $source = $skill.FullName
    $link   = Join-Path $skillsDir $name

    if (-not (Test-Path -LiteralPath $link)) {
        cmd /c mklink /J "`"$link`"" "`"$source`"" | Out-Null
        Write-Host "  created   : $name" -ForegroundColor Green
        $created++
        continue
    }

    $item      = Get-Item -LiteralPath $link -Force
    $isReparse = ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0

    if (-not $isReparse) {
        Write-Host "  conflict  : $name -- a real directory exists at $link (left untouched)" -ForegroundColor Red
        $conflicts++
        continue
    }

    $currentTarget = $item.Target
    if ($currentTarget -is [array]) { $currentTarget = $currentTarget[0] }

    if ($currentTarget -and ($currentTarget -ieq $source)) {
        Write-Host "  ok        : $name (already linked)" -ForegroundColor DarkGray
        $skipped++
        continue
    }

    # Junction exists but points elsewhere, or target couldn't be read -- replace it.
    # `cmd /c rmdir` on a junction removes only the junction, never the target contents.
    cmd /c rmdir "`"$link`"" 2>&1 | Out-Null
    cmd /c mklink /J "`"$link`"" "`"$source`"" | Out-Null

    if ($currentTarget) {
        Write-Host "  retargeted: $name (was -> $currentTarget)" -ForegroundColor Yellow
    } else {
        Write-Host "  recreated : $name" -ForegroundColor Yellow
    }
    $retargeted++
}

Write-Host ""
Write-Host ("Done: {0} created, {1} retargeted, {2} already correct, {3} conflicts" -f `
    $created, $retargeted, $skipped, $conflicts) -ForegroundColor Cyan

if ($conflicts -gt 0) {
    Write-Host ""
    Write-Host "Some skills conflicted with real directories already present in $skillsDir." -ForegroundColor Red
    Write-Host "Move or remove those directories if you want them replaced by this repo's version, then re-run." -ForegroundColor Red
}
