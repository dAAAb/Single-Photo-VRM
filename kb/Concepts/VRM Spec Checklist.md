---
type: concept
verified: 2026-09-29
tags:
  - concept
  - vrm
  - spec
---
VRM 1.0 合格清單（依規格 schema）：

1. `VRMC_vrm` 必要：`specVersion`、`meta`、`humanoid`
2. `meta` 必要：`name`、`authors[]`、`licenseUrl`；明確設定 `avatarPermission`、`commercialUsage` 等
3. **15 根必要骨**：hips、spine、head、左右 upperLeg / lowerLeg / foot、左右 upperArm / lowerArm / hand（完整對應見 [[VRM Humanoid Bones]]）
4. 父子鏈依規格；正 scale；rest pose = 面向 +Z 的 T-pose（add-on 處理方向）
5. 規格選配但 app 期待：表情 preset（aa、ih、ou、ee、oh、blink(L/R)、happy、angry、sad、relaxed、surprised、neutral、lookUp/Down/Left/Right）、lookAt、firstPerson、MToon 或 KHR_materials_unlit、VRMC_springBone
6. **VSeeFace 只吃 VRM0** → 兩版都要出（[[Perfect Sync]]）
7. 驗證：[[vrm-validator]]

工具：[[VRM Add-on for Blender]]。
