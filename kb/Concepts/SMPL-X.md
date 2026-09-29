---
type: concept
verified: 2026-09-29
tags:
  - concept
  - smplx
  - body-model
  - license
---
參數化人體模型（10,475 頂點），幾乎所有單圖人體重建都以它為骨架先驗。

- 頭部 = [[FLAME]] 拓樸（官方對應檔 `SMPL-X__FLAME_vertex_ids.npy`，[vchoutas/smplx](https://github.com/vchoutas/smplx)）
- 骨架對 VRM 見 [[VRM Humanoid Bones]]；權重轉移見 [[SMPL-X Weight Transfer]]

> [!danger] 授權
> **SMPL-X Model license = 非商用**，明文禁止「商業服務」與「為商業目的產生其他產物」；商用授權經 Meshcapade。
> 另有 **SMPL-X Body license（CC-BY 4.0）**：涵蓋以 OBJ/FBX 分享的**單一特定身體**（mesh、骨架、pose blendshape，不含 shape space）→ 單一匯出 avatar 可 CC-BY，但**在商業產品裡跑模型 / 擬合器仍需商用授權**。見 [[Licensing Matrix]]。

Blender 工具：[官方 SMPL-X add-on](https://gitlab.tuebingen.mpg.de/jtesch/smplx_blender_addon)（Blender 4.5+，FBX 匯出給 Unity/Unreal）；Meshcapade SMPL_blender_addon（GPL-3.0，已停更）；[SMPL-to-FBX](https://github.com/softcat477/SMPL-to-FBX)（MIT，2023 停更）；Smplx2FBX（GPL-2.0，研究用）。**找不到現成 smplx→VRM 轉換器，要自己寫。**

> [!tip] 可商用替代
> [[Anny]]（Apache + CC0）、[[Meta MHR]]（Apache）。
