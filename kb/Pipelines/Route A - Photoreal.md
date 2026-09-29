---
type: pipeline
status: planned
tags:
  - pipeline
  - photoreal
---
> [!note] v2：主線改成 [[Template Morphing]]（瀏覽器內、不需 CUDA）；以下 v1 的 CUDA 重建流程改當 T2 加值層（[[Platform Tiers]]）。

重建身體 + 範本頭。細節見 [[Implementation Plan]]。

```
照片 ─┬─ 臉 → MediaPipe → 擬合 ICT identity → UV 投影 + inpaint → ICT 52 表情
      └─ 身 → (A-pose 正規化) → PSHuman → SMPL-X 權重轉移 + unpose → 切頭
                                      ↘ 頸部接合 ↙
                          Blender headless → VRM0 + VRM1
```

1. [[Photo to Face Fitting]] → [[ICT-FaceKit]]
2. [[PSHuman]] → [[SMPL-X Weight Transfer]]
3. [[Head-Body Stitching]]
4. [[VRM Add-on for Blender]]，命名依 [[Perfect Sync]]，骨架依 [[VRM Humanoid Bones]]
5. [[vrm-validator]] + [[three-vrm]] + iPhone 實測

商用版替換：見 [[Licensing Matrix]]。
