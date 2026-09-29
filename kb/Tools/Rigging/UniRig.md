---
type: tool
stage: rig
url: https://github.com/VAST-AI-Research/UniRig
stars: 1779
license_code: "MIT"
license_weights: "MIT"
commercial: "✓"
last_update: 2026-06
verified: 2026-09-29
tags:
  - tool
  - rigging
  - generic-skeleton
---
SIGGRAPH 2025 TOG（arXiv 2504.12451），清華 + VAST/Tripo。CLI：`generate_skeleton.sh` / `generate_skin.sh` / `merge.sh`，≥8 GB CUDA。

  > [!warning]
  > - 釋出權重為 Articulation-XL2.0；**Rig-XL/VRoid checkpoint 仍 pending**
  > - 預測的是**通用骨架、非 humanoid 命名** → 無法直接對 VRM
  > - README 已推後繼 SkinTokens（437★ MIT）

  - ComfyUI-UniRig（PozzettiAndrea，424★，**GPL-3.0**）內含 [[Make-It-Animatable]]，建議人型用 MIA
  - 用改版 VRM Blender add-on 讀寫 `.vrm`；spring bone 預測仍 "planned"
