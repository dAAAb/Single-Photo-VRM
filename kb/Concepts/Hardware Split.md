---
type: concept
verified: 2026-09-29
tags:
  - concept
  - infra
---
> [!warning] 所有單圖人體重建模型都需要 CUDA（gsplat、nvdiffrast、pytorch3d），沒有 README 提到 MPS。

| 工作 | 位置 |
|---|---|
| 匯出（[[VRM Add-on for Blender]]）、驗證、預覽 | M4 Max |
| 臉部擬合（MediaPipe + 優化，[[Photo to Face Fitting]]）| M4 Max |
| [[SMPL-X Weight Transfer]]、[[Head-Body Stitching]] | M4 Max |
| [[PSHuman]]（>40 GB）、[[StdGEN]]（24 GB）、[[Make-It-Animatable]] | Nebius / Brev H100 |
