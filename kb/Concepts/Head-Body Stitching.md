---
type: concept
verified: 2026-09-29
tags:
  - concept
  - face
  - body
  - open-problem
---
把 [[ICT-FaceKit]] 擬合頭接到重建身體上。**找不到開源參考實作**（Avaturn / MetaPerson 皆閉源）。

建議做法：
1. 身體對齊 [[SMPL-X]] → 用 SMPL-X↔[[FLAME]] 對應定位頭
2. 切掉重建頭部至頸環
3. 2–3 cm 帶用 RBF / Laplacian 混合縫合
4. 頸部用 SMPL-X 權重
5. UV 空間 color transfer / Poisson 融膚色

ECON 的換臉技巧可參考但非商用。

> [!tip] v2：變成一次性工作
> 在 [[Template Morphing]] 架構下，頭（[[ICT-FaceKit]]）和身體（[[Anny]]）拓樸都是固定的，接縫只在做範本時處理一次；每張照片只需要讓接縫帶跟著兩邊的變形平滑過渡。
