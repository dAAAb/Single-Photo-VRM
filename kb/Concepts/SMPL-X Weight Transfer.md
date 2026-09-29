---
type: concept
verified: 2026-09-29
tags:
  - concept
  - smplx
  - rigging
  - key-insight
---
> [!tip] 本專案關鍵洞見（Grok 漏掉）
> 重建模型本來就對齊 [[SMPL-X]] → **直接沿用 SMPL-X 骨架與 LBS 權重**，不用再跑一次自動綁骨。確定性、含手指、**不需 GPU、Mac 可跑**。

- **同拓樸**（10,475 頂點對齊）：權重 1:1 複製，免最近點
- **穿衣 / 偏移表面**（如 [[PSHuman]] 輸出）：最近點 / Blender Data Transfer / robust weight transfer，再平滑
- 再用 inverse LBS 把 posed mesh unpose 成 T-pose
- 關節改名對 VRM：[[VRM Humanoid Bones]]
- 參考實作：[[ECON]] avatarizer（非商用）

風險：unpose 在腋下 / 胯下 / 寬鬆衣服會破面 → [[Implementation Plan]] Phase 3 實驗「先把輸入照片正規化成 A-pose」。

非 SMPL-X mesh 的備案：[[Make-It-Animatable]]。
