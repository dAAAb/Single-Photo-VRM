---
type: concept
verified: 2026-09-29
tags:
  - concept
  - architecture
  - key-insight
---
> [!tip] v2 核心架構
> 不在執行時生成 3D，而是**改寫一個事先做好的範本 VRM**：擬合參數 → patch 頂點 / 骨頭 → 投影貼圖。整條 pipeline 都能在瀏覽器裡跑。

**開發時一次性（Blender）**：[[Anny]]（身體 + 臉都用它；2026-09-29 spike 後不再接 ICT 頭）→ 52 ARKit morph + VRM preset + eye bones + spring bone → `template.vrm`（[[VRM Add-on for Blender]]）

**每張照片（瀏覽器）**：
1. [[MediaPipe Tasks Vision]]：478 臉點、33 身體點、髮 / 膚 / 衣分割
2. JS LM 擬合：Anny 臉部 local change + 身材參數 + 頭部姿態（臉部 local change 的自由度待評估）
3. [[GLB Patching]]：base 頂點、骨頭 translation、inverseBindMatrices
4. UV 投影 + LaMa 補洞（[[ONNX Runtime Web and transformers.js]]）
5. 下載 VRM0 + VRM1

**為什麼成立**
- 兩個模型都是線性的；glTF morph target 本身就是 delta → 換臉型後 52 個表情照樣正確（形狀差異很大時可能需要微調，待驗證）
- 拓樸固定 → 頭身接縫只在範本裡做一次（[[Head-Body Stitching]] 從每張照片都要處理，變成一次性工作）
- 擬合規模約 1434 殘差 × 107 未知數 → 純 JS 幾十 ms（估計值）
- 不需 CUDA、不需伺服器、預設全線可商用

**代價**：衣服是貼在身體上的貼圖、頭髮靠零件庫、側臉深度不準 → 這些要靠 [[Platform Tiers]] 的 T1/T2 補。

業界印證：MetaPerson / Avaturn 走的也是範本擬合（[[Commercial Baselines]]）。
