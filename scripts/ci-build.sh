#!/usr/bin/env bash
# Build standalone extension zip + release bundle (same as CI).
exec "$(dirname "$0")/package-release.sh" "$@"
