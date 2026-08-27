#!/usr/bin/env bash
# Validate and build the Blender extension zip (same steps as GitHub Actions).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v blender >/dev/null 2>&1; then
  echo "error: blender not on PATH (need Blender 5.2+)" >&2
  exit 1
fi

echo "==> extension validate"
blender --command extension validate

echo "==> extension build"
blender --command extension build

ZIP="$(ls -1 export_3ds_tmf-*.zip 2>/dev/null | sort -V | tail -n 1 || true)"
if [[ -z "$ZIP" ]]; then
  echo "error: no export_3ds_tmf-*.zip produced" >&2
  exit 1
fi

echo "==> built ${ZIP} ($(wc -c < "$ZIP") bytes)"
