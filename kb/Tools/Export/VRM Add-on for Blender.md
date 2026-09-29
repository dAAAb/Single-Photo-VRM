---
type: tool
stage: export
url: https://github.com/saturday06/VRM-Addon-for-Blender
stars: 1713
license_code: "MIT / GPL-3.0+"
license_weights: "—"
commercial: "✓"
last_update: 2026-09-28
verified: 2026-09-29
tags:
  - tool
  - export
  - headless
  - recommended
---
> [!tip] 匯出核心：不需 Unity
  > v4.9.1（2026-09-28）。PyPI [`bpy-vrm-format`](https://pypi.org/project/bpy-vrm-format/) 內含 bpy，**不必安裝 Blender**。

  [Scripting API](https://vrm-addon-for-blender.info/en-us/scripting-api/)（名稱已對原始碼，**尚未實跑** → [[Implementation Plan]] Phase 0）：
  - 骨架：`armature.data.vrm_addon_extension.vrm1.humanoid.human_bones.<bone>.node.bone_name`；`bpy.ops.vrm.assign_vrm1_humanoid_human_bones_automatically`
  - 表情：`vrm1.expressions.preset.{aa,ih,…}.morph_target_binds`；`vrm.assign_vrm1_expressions_from_arkit`；`vrm.assign_vrm1_expressions_automatically`
  - spring bone：`spring_bone1.{springs[].joints, colliders, collider_groups}`
  - `vrm1.look_at`、`vrm1.first_person`、`vrm1.meta`；材質 `mtoon1`
  - 匯出：`bpy.ops.export_scene.vrm(filepath=…)`（1.0 預設，可選 0.x）；`bpy.ops.export_scene.vrma`

  支援 Blender 2.93–5.2。規格見 [[VRM Spec Checklist]]。
