#!/usr/bin/env bash
# Build the Perfect Sync template VRM (VRM 1.0 + 0.x) from Anny.
# Requires: template/.venv (uv venv + anny), Blender 5.x, VRM Add-on installed in build/blender_user.
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(cd .. && pwd)
BLENDER=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
mkdir -p "$ROOT/build"

if [ ! -d .venv ]; then
  uv venv -q -p 3.12 .venv
  uv pip install -q -p .venv/bin/python -e "$ROOT/third_party/anny" trimesh numpy
fi
if [ ! -d "$ROOT/build/blender_user/extensions" ]; then
  curl -sL -o "$ROOT/build/vrm_ext.zip" \
    https://github.com/saturday06/VRM-Addon-for-Blender/releases/download/v4.7.2/VRM_Addon_for_Blender-Extension-4_7_2.zip
  BLENDER_USER_RESOURCES="$ROOT/build/blender_user" "$BLENDER" -b --python-expr \
    "import bpy,sys; bpy.ops.extensions.package_install_files(filepath='$ROOT/build/vrm_ext.zip', repo='user_default', enable_on_install=True); bpy.ops.wm.save_userpref()"
fi

.venv/bin/python export_anny.py --out "$ROOT/build/anny_tpose.npz"
BLENDER_USER_RESOURCES="$ROOT/build/blender_user" "$BLENDER" -b --python build_vrm.py -- \
  "$ROOT/build/anny_tpose.npz" "$ROOT/build/template"
mkdir -p "$ROOT/viewer/public/samples"
cp "$ROOT/build/template.vrm1.vrm" "$ROOT/build/template.vrm0.vrm" "$ROOT/viewer/public/samples/"
echo "→ build/template.vrm1.vrm, build/template.vrm0.vrm (also copied to viewer/public/samples/)"
