---
type: tool
stage: face
url: https://github.com/ICT-VGL/ICT-FaceKit
license_code: "**MIT**"
license_weights: "MIT"
commercial: "✓"
last_update: —
verified: 2026-09-29
tags:
  - tool
  - face
  - template-head
  - arkit
  - commercial-clean
  - recommended
---
> [!tip] 本專案臉部核心
  > 唯一 MIT 且同時具備 **眼球 + 口腔 + 牙齒 + 舌頭 + ARKit 表情** 的範本頭。

  | 內容 | 有無 |
  |---|---|
  | 眼球、鞏膜、淚液、遮擋 mesh、睫毛 | ✓ |
  | 口腔、牙齦 + 舌頭、32 顆牙 | ✓ |
  | ARKit 表情 | 53 個 OBJ，ARKit 命名 `_L/_R` |
  | identity | 100 個 PCA mode（**無 albedo model**） |

  **要處理的差異**（見 [[Perfect Sync]]）：
  - `browInnerUp`、`cheekPuff` 分成 L/R → 合併
  - 多出 `cheekRaiser`、`PupilDilate`
  - **缺 `tongueOut`** → 在範本上手雕一次

  保留 ICT 拓樸就**不需要 deformation transfer**，直接套表情 delta。
  擬合方式見 [[Photo to Face Fitting]]。
