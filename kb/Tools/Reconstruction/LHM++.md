---
type: tool
stage: body
url: https://github.com/aigc3d/LHM-plusplus
stars: 693
license_code: "Apache-2.0"
license_weights: "**CC BY-NC 4.0**"
commercial: "✗"
last_update: 2026-05
verified: 2026-09-29
tags:
  - tool
  - reconstruction
  - 3dgs
  - smplx
---
2026-03 釋出。單圖 **0.79 s / 8 GB VRAM**。`scripts/inference/to_gs_ply.py` 匯出 **canonical T-pose 3DGS PLY（SMPL-X 空間）**。

  > [!danger] 授權
  > `LICENSE_WEIGHT` = CC BY-NC 4.0；預設 PixelShuffle 權重仍標 "Hub weights pending"。

  - 在 [[Implementation Plan]] Phase 3 作為研究對照組：T-pose Gaussian → 多視角渲染 → 轉 mesh（未驗證的混合想法）
