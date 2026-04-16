#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Push wiki/ directory contents to the GitHub Wiki repository.
.DESCRIPTION
    This script initializes or updates the GitHub Wiki for consilium-fabri.
    Prerequisites: The wiki must be initialized through the GitHub web UI first.
    Go to https://github.com/arcobaleno64/consilium-fabri/wiki and create the first page.
#>

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$wikiSource = Join-Path $repoRoot 'wiki'
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) "cf-wiki-push-$(Get-Random)"

if (-not (Test-Path $wikiSource)) {
    Write-Error "wiki/ directory not found at $wikiSource"
    exit 1
}

Write-Host "Cloning wiki repository..." -ForegroundColor Cyan
try {
    git clone https://github.com/arcobaleno64/consilium-fabri.wiki.git $tempDir 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Failed to clone wiki repo. Have you created the first page at https://github.com/arcobaleno64/consilium-fabri/wiki ?" }
} catch {
    Write-Error $_
    exit 1
}

Write-Host "Copying wiki pages..." -ForegroundColor Cyan
Get-ChildItem "$tempDir\*" -Exclude '.git' | Remove-Item -Recurse -Force
Copy-Item "$wikiSource\*" $tempDir -Recurse -Force

Set-Location $tempDir
git add -A
$changes = git status --porcelain
if (-not $changes) {
    Write-Host "No changes to push." -ForegroundColor Yellow
    exit 0
}

git commit -m "docs: update wiki from repo wiki/ directory"
git push origin master

Write-Host "Wiki updated successfully." -ForegroundColor Green
Write-Host "View at: https://github.com/arcobaleno64/consilium-fabri/wiki" -ForegroundColor Cyan

Set-Location $repoRoot
Remove-Item $tempDir -Recurse -Force
