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
- **Face Units 實測（v0.6，2026-09-29）**：`facial_actions="all"` → 52 個，**和 ARKit 52 完全一致**（不多不少）
- **牙齒**：`topology="anny-full"` 保留 MakeHuman 輔助幾何，但 `model.faces` 不含它們 → 從 `data/mpfb2/3dobjs/base.obj` 的 `helper-upper-teeth` / `helper-lower-teeth` 群組讀面（各 48 個四邊形、68 頂點；UV 索引和 Anny 一致）。下排牙會被 jawOpen / jawLeft / jawForward 帶動，上排不動；權重在 head / neck01
- 網格：13,718 頂點 / 27,420 三角面；4 個連通塊 = 身體 + **舌頭（226）** + **左右眼球（各 72）**；**沒有牙齒**
- 表情作用範圍：jawOpen 2,409 點（有口腔）、tongueOut 只動舌頭 226 點、eyeBlinkLeft 717 點
- rig：104 骨（anny rig）；靜止姿勢是 A-pose（手臂往下約 48°、手肘前彎）→ 用 `pose_parameterization="world-orient"` 轉成 T-pose
- 座標：Z 軸朝上、臉朝 -Y（和 Blender 的慣例一樣）、原點在骨盆
- 有 UV（21,334 個 UV 座標）；MPFB2 附了嘴唇、眼瞼、口腔內部等局部貼圖，**沒有完整的皮膚貼圖**
- 骨頭對應見 `template/export_anny.py` 的 `VRM_BONES`；finger1 = 拇指，finger2–5 = 食指到小指
- **不要**用 SMPL-X 拓樸選項（非商用）

[[Template Morphing]] 的**身體 + 臉**範本（不再需要 [[ICT-FaceKit]]）。
