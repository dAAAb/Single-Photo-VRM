---
type: tool
stage: body
url: https://github.com/aigc3d/LHM
stars: 2678
license_code: "Apache-2.0"
license_weights: "Apache-2.0"
commercial: "受 SMPL-X 限制"
last_update: 2026-03
verified: 2026-09-29
tags:
  - tool
  - reconstruction
  - 3dgs
  - smplx
---
ICCV 2025，阿里通義。單圖 feed-forward → **綁 SMPL-X 的 3D Gaussian**，1.4–6.6 s，14–24 GB VRAM，需 CUDA。

  > [!warning] Grok 說法錯誤
  > `inference_mesh.sh` → `infer_mesh()` 實際呼叫 `save_ply()`，輸出的是 **SMPL-X zero-pose 的 Gaussian .ply，不是三角網格**。見 [[Grok Claims Verification]]。

  - 有 `feat/comfyui` 分支
  - 後繼：[[LHM++]]；前身：[[AniGS]]
  - 對本專案：Gaussian 無法直接當 VRM mesh，且沒有眼球/口腔 → 不適合 [[Perfect Sync]]
