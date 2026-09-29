---
type: tool
stage: rig
url: https://github.com/jasongzy/Make-It-Animatable
stars: 458
license_code: "MIT"
license_weights: "Apache-2.0"
commercial: "✓（v1）"
last_update: 2026-09-08
verified: 2026-09-29
tags:
  - tool
  - rigging
  - humanoid
  - commercial-clean
  - recommended
---
CVPR 2025，簡稱 MIA。mesh 或 3DGS 都吃，<1 s。

  > [!tip] 非 SMPL-X mesh 的綁骨首選
  > 輸出 **Mixamo 65 骨命名（含手指）**（見 `app.py`）→ 直接對 [[VRM Humanoid Bones]]。

  - v2 分支改用 Hunyuan3D 2.1 ShapeVAE → 帶 Tencent 授權；**用 v1 main**
  - Gradio app，函式可直接呼叫；用 bpy + FBX2glTF；CUDA 導向
  - 也被包在 [[UniRig]] 的 ComfyUI 節點（GPL-3.0）
