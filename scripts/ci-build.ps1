# Validate and build the Blender extension zip (Windows / local dev).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))

$blender = Get-Command blender -ErrorAction SilentlyContinue
if (-not $blender) {
    $fallback = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
    if (Test-Path $fallback) { $blender = $fallback } else { throw "blender not found on PATH" }
} else {
    $blender = $blender.Source
}

Write-Host "==> extension validate"
& $blender --command extension validate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> extension build"
& $blender --command extension build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$zip = Get-ChildItem -Filter "export_3ds_tmf-*.zip" | Sort-Object Name | Select-Object -Last 1
if (-not $zip) { throw "no export_3ds_tmf-*.zip produced" }
Write-Host "==> built $($zip.Name) ($($zip.Length) bytes)"
