---
type: moc
tags:
  - moc
---
# Single-Photo-VRM 知識庫

一張照片 → 帶 **humanoid 骨架 + [[Perfect Sync]] 臉部表情**的 VRM。調研日期 2026-09-29，全部一手來源查證。

## 從這裡開始
- [[Implementation Plan]]：架構與開發階段
- [[Research Survey]]：完整調研報告（單篇長文版）
- [[Grok Claims Verification]]：Grok 建議逐項查證

## 核心結論
1. 沒有開源工具能一步到位 → 架構是「重建身體 + 範本頭」
2. 單圖重建的頭沒有眼球、口腔 → 臉用 [[ICT-FaceKit]]（MIT）
3. 身體直接沿用 SMPL-X 骨架 → [[SMPL-X Weight Transfer]]
4. 不需 Unity → [[VRM Add-on for Blender]]（`pip install bpy-vrm-format`）
5. 授權是地雷 → [[Licensing Matrix]]

## 路線
- [[Legacy PIFuHD + Mixamo]]（舊）
- [[Route A - Photoreal]]
- [[Route B - Anime]]

## 概念
[[Perfect Sync]] · [[VRM Spec Checklist]] · [[VRM Humanoid Bones]] · [[SMPL-X]] · [[SMPL-X Weight Transfer]] · [[Head-Body Stitching]] · [[Anime Template Assembly]] · [[Licensing Matrix]] · [[Hardware Split]]

## 工具
- **重建**：[[PSHuman]] · [[LHM]] · [[LHM++]] · [[IDOL]] · [[DiGS-Avatar]] · [[AniGS]] · [[SyncHuman]] · [[SiTH]] · [[ECON]] · [[GeneMAN]] · [[HumanLift]] · [[PERSONA]] · [[TRELLIS.2]] · [[SAM 3D Body]]
- **綁骨**：[[Make-It-Animatable]] · [[UniRig]] · [[AniGen]] · [[Mesh2Motion]] · [[Other Auto-Riggers]]
- **臉**：[[ICT-FaceKit]] · [[FLAME]] · [[Photo to Face Fitting]] · [[ARKit Shape Generation]]
- **匯出 / 預覽**：[[VRM Add-on for Blender]] · [[UniVRM]] · [[three-vrm]] · [[vrm-validator]]
- **動作**：[[HY-Motion 1.0]] · [[VRMA Tools]]
- **二次元**：[[StdGEN]] · [[CharacterGen]] · [[PAniC-3D]] · [[hinzka 52blendshapes]] · [[blender-vrm-perfect-sync]]
- **商用**：[[Commercial Baselines]]

## Dataview（需安裝 Dataview 外掛）
```dataview
TABLE stage, stars, license_code, license_weights, commercial, last_update
FROM "Tools"
SORT stage ASC, stars DESC
```
