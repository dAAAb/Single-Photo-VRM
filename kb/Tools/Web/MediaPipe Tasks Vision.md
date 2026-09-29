---
type: tool
stage: perception
url: https://www.npmjs.com/package/@mediapipe/tasks-vision
license_code: "Apache-2.0"
license_weights: "模型卡 CC-BY-4.0（multiclass seg）"
commercial: "✓"
last_update: 1.0.1
verified: 2026-09-29
tags:
  - tool
  - web
  - web
  - recommended
---
`@mediapipe/tasks-vision` 1.0.1（Python 版 1.0.1 在 macOS arm64 / Linux / Windows 都有 wheel）。

| Task | 輸出 |
|---|---|
| Face Landmarker | 478 點；`outputFaceBlendshapes` → **52 個 ARKit 風格值**；`outputFacialTransformationMatrixes`（預設都關閉）|
| Pose Landmarker | 33 點 + world landmarks + 分割 |
| Image Segmenter SelfieMulticlass 256² | 0 背景、1 頭髮、2 身體皮膚、3 臉部皮膚、4 衣服、5 其他 |

- `delegate:"GPU"`（WebGL2 系）；官方只列 **Chrome、Safari**
- `detect()` 是同步的 → 放 Worker 跑
- **webcam blendshape → 範本 morph = 瀏覽器內就能預覽 [[Perfect Sync]]**（[[Implementation Plan]] Phase 1）
- 需一次性標註 478 點 ↔ [[ICT-FaceKit]] 頂點對應
