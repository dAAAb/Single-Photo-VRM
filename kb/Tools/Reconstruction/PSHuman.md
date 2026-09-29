---
type: tool
stage: body
url: https://github.com/pengHTYX/PSHuman
stars: 462
license_code: "MIT"
license_weights: "HF"
commercial: "受 SMPL-X 限制"
last_update: 2024-12
verified: 2026-09-29
tags:
  - tool
  - reconstruction
  - mesh
  - smplx
  - recommended
---
> [!tip] 本專案寫實身體首選
  > 輸出**有貼圖 mesh，且與其擬合的 SMPL-X 對齊**（`with_smpl=true`）→ [[SMPL-X Weight Transfer]] 最省事。

  - **>40 GB VRAM**，約 1 min/張 → 需 A100/H100（見 [[Hardware Split]]）
  - 輸出為照片姿勢（posed），需 unpose
  - 頭部為封閉表面 → 要換成 [[ICT-FaceKit]] 頭（[[Head-Body Stitching]]）
  - 最後更新 2024-12，需注意環境相依
