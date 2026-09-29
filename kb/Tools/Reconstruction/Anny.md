---
type: tool
stage: body
url: https://github.com/naver/anny
license_code: "Apache-2.0"
license_weights: "MPFB2/MakeHuman CC0 + Face Units CC0（SMPL-X 拓樸選項 = 非商用）"
commercial: "✓"
last_update: 2025-11
verified: 2026-09-29
tags:
  - tool
  - reconstruction
  - body-model
  - commercial-clean
  - recommended
---
NAVER LABS（arXiv 2511.03589）。**取代 [[SMPL-X]] 的可商用身體模型。**

- 可解釋的外型滑桿：年齡、性別、身高、體重…
- rig：104 骨 anny rig 或 163 骨完整 MakeHuman rig → 對 [[VRM Humanoid Bones]]
- 目前只有 PyTorch、沒有 JS 版；但它是線性 blendshape + LBS，**移植成 JS 很直接**
- Face Units：傳聞有 ARKit 系 shape（未驗證）→ [[Implementation Plan]] Phase 0 spike
- **不要**用 SMPL-X 拓樸選項（非商用）

[[Template Morphing]] 的身體範本。
