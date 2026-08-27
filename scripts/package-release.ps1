# Stage extension, build zips, and assemble export_3ds_tmf-{version}-bundle.zip
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$blender = Get-Command blender -ErrorAction SilentlyContinue
if (-not $blender) {
    $fallback = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
    if (Test-Path $fallback) { $blender = $fallback } else { throw "blender not found on PATH" }
} else {
    $blender = $blender.Source
}

$manifest = Get-Content "blender_manifest.toml" -Raw
if ($manifest -match '(?m)^version\s*=\s*"([^"]+)"') {
    $Version = $Matches[1]
} else {
    throw "could not read version from blender_manifest.toml"
}

$ExtId = "export_3ds_tmf"
$ExtZip = "$ExtId-$Version.zip"
$BundleZip = "$ExtId-$Version-bundle.zip"
$Stage = Join-Path $Root "build\extension"
$Bundle = Join-Path $Root "build\bundle"

$ExtensionFiles = @(
    "blender_manifest.toml",
    "__init__.py",
    "addon_info.py",
    "export_operator.py",
    "import_operator.py",
    "exporter.py",
    "importer.py",
    "format_3ds.py",
    "material_utils.py",
    "tmf_validation.py",
    "tmf_scene.py",
    "tmf_helpers.py",
    "ui_panel.py"
)

Write-Host "==> packaging $ExtId v$Version"

if (Test-Path (Join-Path $Root "build")) { Remove-Item -Recurse -Force (Join-Path $Root "build") }
New-Item -ItemType Directory -Force -Path $Stage | Out-Null

foreach ($f in $ExtensionFiles) {
    $src = Join-Path $Root $f
    if (-not (Test-Path $src)) { throw "missing extension file $f" }
    Copy-Item $src (Join-Path $Stage $f)
}

Write-Host "==> extension validate (staged)"
Push-Location $Stage
& $blender --command extension validate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> extension build (staged)"
& $blender --command extension build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Pop-Location

$built = Get-ChildItem -Path $Stage -Filter "$ExtId-*.zip" | Select-Object -First 1
if (-not $built) { throw "extension zip not produced in build/extension" }

Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $Root $ExtZip), (Join-Path $Root $BundleZip)
Copy-Item $built.FullName (Join-Path $Root $ExtZip)

New-Item -ItemType Directory -Force -Path (Join-Path $Bundle "template"), (Join-Path $Bundle "script") | Out-Null
Copy-Item (Join-Path $Root "template\base-tmf-scene.blend") (Join-Path $Bundle "template\")
Copy-Item (Join-Path $Root $ExtZip) (Join-Path $Bundle "script\$ExtZip")
Copy-Item (Join-Path $Root "README.md") (Join-Path $Bundle "README.MD")
Copy-Item (Join-Path $Root "docs\TUTORIAL.md") (Join-Path $Bundle "TUTORIAL.MD")

$required = @(
    (Join-Path $Bundle "template\base-tmf-scene.blend"),
    (Join-Path $Bundle "script\$ExtZip"),
    (Join-Path $Bundle "README.MD"),
    (Join-Path $Bundle "TUTORIAL.MD")
)
foreach ($path in $required) {
    if (-not (Test-Path $path)) { throw "bundle missing $path" }
}

Write-Host "==> create bundle zip"
if (Test-Path (Join-Path $Root $BundleZip)) { Remove-Item -Force (Join-Path $Root $BundleZip) }
Push-Location $Bundle
try {
    Compress-Archive -Path * -DestinationPath (Join-Path $Root $BundleZip) -Force
} finally {
    Pop-Location
}

Write-Host "==> verify standalone extension zip excludes template blend"
$extListing = & tar -tf (Join-Path $Root $ExtZip) 2>$null
if ($extListing -match 'base-tmf-scene') {
    throw "extension zip must not contain base-tmf-scene.blend"
}

Write-Host "==> verify bundle layout"
$bundleListing = & tar -tf (Join-Path $Root $BundleZip)
$mustHave = @(
    "template/base-tmf-scene.blend",
    "script/$ExtZip",
    "README.MD",
    "TUTORIAL.MD"
)
foreach ($entry in $mustHave) {
    if ($bundleListing -notcontains $entry) {
        throw "bundle zip missing $entry"
    }
}

Write-Host "==> built:"
Write-Host "    $(Join-Path $Root $ExtZip) $((Get-Item (Join-Path $Root $ExtZip)).Length) bytes"
Write-Host "    $(Join-Path $Root $BundleZip) $((Get-Item (Join-Path $Root $BundleZip)).Length) bytes"
