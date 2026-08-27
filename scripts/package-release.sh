#!/usr/bin/env bash
# Stage extension, build zips, and assemble export_3ds_tmf-{version}-bundle.zip
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v blender >/dev/null 2>&1; then
  echo "error: blender not on PATH (need Blender 5.2+)" >&2
  exit 1
fi

VERSION="$(grep -E '^version\s*=' blender_manifest.toml | sed -E 's/^version\s*=\s*"([^"]+)".*/\1/')"
EXT_ID="export_3ds_tmf"
EXT_ZIP="${EXT_ID}-${VERSION}.zip"
BUNDLE_ZIP="${EXT_ID}-${VERSION}-bundle.zip"
STAGE="${ROOT}/build/extension"
BUNDLE="${ROOT}/build/bundle"

EXTENSION_FILES=(
  blender_manifest.toml
  __init__.py
  addon_info.py
  export_operator.py
  import_operator.py
  exporter.py
  importer.py
  format_3ds.py
  material_utils.py
  tmf_validation.py
  tmf_scene.py
  tmf_helpers.py
  ui_panel.py
)

echo "==> packaging ${EXT_ID} v${VERSION}"

rm -rf "$STAGE" "$BUNDLE"
mkdir -p "$STAGE"

for f in "${EXTENSION_FILES[@]}"; do
  if [[ ! -f "$ROOT/$f" ]]; then
    echo "error: missing extension file $f" >&2
    exit 1
  fi
  cp "$ROOT/$f" "$STAGE/"
done

echo "==> extension validate (staged)"
(cd "$STAGE" && blender --command extension validate)

echo "==> extension build (staged)"
(cd "$STAGE" && blender --command extension build)

BUILT_ZIP="$(ls -1 "$STAGE/${EXT_ID}-"*.zip | head -n 1)"
if [[ ! -f "$BUILT_ZIP" ]]; then
  echo "error: extension zip not produced in $STAGE" >&2
  exit 1
fi

rm -f "$ROOT/$EXT_ZIP" "$ROOT/$BUNDLE_ZIP"
cp "$BUILT_ZIP" "$ROOT/$EXT_ZIP"

mkdir -p "$BUNDLE/template" "$BUNDLE/script"
cp "$ROOT/template/base-tmf-scene.blend" "$BUNDLE/template/"
cp "$ROOT/$EXT_ZIP" "$BUNDLE/script/$EXT_ZIP"
cp "$ROOT/README.md" "$BUNDLE/README.MD"
cp "$ROOT/docs/TUTORIAL.md" "$BUNDLE/TUTORIAL.MD"

for req in \
  "$BUNDLE/template/base-tmf-scene.blend" \
  "$BUNDLE/script/$EXT_ZIP" \
  "$BUNDLE/README.MD" \
  "$BUNDLE/TUTORIAL.MD"
do
  if [[ ! -f "$req" ]]; then
    echo "error: bundle missing $req" >&2
    exit 1
  fi
done

echo "==> create bundle zip"
(cd "$BUNDLE" && zip -r "$ROOT/$BUNDLE_ZIP" .)

echo "==> verify standalone extension zip excludes template blend"
if unzip -l "$ROOT/$EXT_ZIP" | grep -qi 'base-tmf-scene'; then
  echo "error: extension zip must not contain base-tmf-scene.blend" >&2
  exit 1
fi

echo "==> verify bundle layout"
unzip -l "$ROOT/$BUNDLE_ZIP" | grep -E 'template/base-tmf-scene\.blend|script/'"${EXT_ID}"'|README\.MD|TUTORIAL\.MD'

echo "==> built:"
echo "    $ROOT/$EXT_ZIP ($(wc -c < "$ROOT/$EXT_ZIP") bytes)"
echo "    $ROOT/$BUNDLE_ZIP ($(wc -c < "$ROOT/$BUNDLE_ZIP") bytes)"
