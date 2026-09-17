#!/usr/bin/env bash
# Builds a clean release archive for copying to a Jetson AGX Orin device.
# Usage: bash scripts/package_jetson_release.sh
set -euo pipefail
cd "$(dirname "$0")/.."

OUT="SynexAgent-YMAS-RC1-Jetson-AGX-Orin.tar.gz"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

echo "Staging release contents in $STAGE"
mkdir -p "$STAGE/SynexAgent"
# Only what a Jetson deployment actually needs -- explicitly enumerated rather than "copy
# everything and exclude a blocklist", so nothing new added to the repo later is accidentally
# swept into a release archive without a deliberate decision to include it here.
for item in backend scripts config docs VERSION .env.example; do
  if [ -e "$item" ]; then
    mkdir -p "$STAGE/SynexAgent/$(dirname "$item")"
    cp -r "$item" "$STAGE/SynexAgent/$item"
  fi
done
mkdir -p "$STAGE/SynexAgent/frontend"
cp -r frontend/dist "$STAGE/SynexAgent/frontend/dist"

# Defense in depth: even though the source list above never included any of these, explicitly
# remove anything that might have been dragged in as a subdirectory of an included path (e.g. a
# stray __pycache__ under backend/app).
find "$STAGE/SynexAgent" -type d \( -name '__pycache__' -o -name '.pytest_cache' -o -name 'node_modules' \
  -o -name '.venv' -o -name '.venv-jetson' -o -name 'runtime' -o -name 'onnxruntime-src' \) -prune -exec rm -rf {} + 2>/dev/null || true
find "$STAGE/SynexAgent" -type f \( -name '*.sqlite3*' -o -name '*.sqlite' -o -name '*.db' -o -name '*.engine' -o -name '.env' \) -delete

echo "Contents check -- confirming no runtime/secret files slipped in:"
if find "$STAGE/SynexAgent" -iname '*.sqlite*' -o -iname '.env' -o -iname '*.engine' | grep -q .; then
  echo "REFUSING TO PACKAGE: found a runtime/secret-shaped file in the staged tree."
  find "$STAGE/SynexAgent" -iname '*.sqlite*' -o -iname '.env' -o -iname '*.engine'
  exit 1
fi
echo "clean."

tar -C "$STAGE" -czf "$OUT" SynexAgent
echo "Wrote $OUT ($(du -h "$OUT" | cut -f1))"
# `tar -tzf "$OUT" | head -20` under `set -euo pipefail` can exit 141 (SIGPIPE) when `head` closes
# its read end after 20 lines while tar is still writing -- `sed -n` reads to EOF instead, so tar
# always exits 0 on its own and the pipeline's exit status is never a pipe-closure artifact.
tar -tzf "$OUT" | sed -n '1,20p'
echo "... ($(tar -tzf "$OUT" | wc -l) entries total)"
