#!/usr/bin/env bash
# Regression run: every image in test_images/ through the full pipeline, then a QA contact sheet.
set -uo pipefail
cd "$(dirname "$0")"
for f in ../test_images/*.{png,jpg,jpeg,webp}; do
  [ -e "$f" ] || continue
  .venv/bin/python photo2vrm.py "$f" 2>&1 | grep -E "photo2vrm|Error|failed" || echo "FAILED $f"
done
.venv/bin/python qa_sheet.py
