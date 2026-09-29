---
type: concept
verified: 2026-09-29
tags:
  - concept
  - anime
  - opportunity
---
> [!note] 調研發現的空缺：**還沒有人做**
> 沒有公開 paper / repo 從照片預測 VRoid 參數。VRoid Studio 無 API、`.vroid` 格式未公開。

可行版本（跳過 VRoid Studio）：
1. 準備**有授權的零件庫**：base VRM 身體（含 52 ARKit，如 [[hinzka 52blendshapes]]）+ 已掛 spring bone 的頭髮 / 服裝
2. VLM / 分類器看照片 → 挑零件、調色
3. 臉 / 眼貼圖：img2img 生成在 VRoid UV 版型上
4. [[blender-vrm-perfect-sync]] 補齊表情 → 匯出

**保證輸出合格 VRM**（blendshape、spring bone、MToon 全有）。

現有積木：PAniC-3D 的 VRoid 資料集（11.2k）、[[StdGEN]] 分層、[[UniRig]] 的 VRoid 訓練資料、[[three-vrm]]、[[VRM Add-on for Blender]]。

便宜混合版：VRoid base 身體 + 頭，只用 [[StdGEN]] 生成頭髮 / 衣服並綁到範本上。

實務界現況（note.com 尾仲ゆる 2026 版）：Nano Banana 轉 A-pose → Tripo 3.0 → Mixamo → Blender VRM add-on → VRMRemaker 降 0.x，約 30 分鐘，**沒有 BlendShape**、權重失敗、貼圖遺失。
