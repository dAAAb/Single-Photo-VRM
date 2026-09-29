---
type: concept
verified: 2026-09-29
tags:
  - concept
  - vrm
  - smplx
  - skeleton
---
[[SMPL-X]] joint → VRM 1.0 humanoid，基本 1:1、含手指：

| SMPL-X | VRM 1.0 |
|---|---|
| pelvis | hips |
| spine1 / spine2 / spine3 | spine / chest / upperChest |
| neck / head / jaw | neck / head / jaw |
| left_eye_smplhf / right_eye_smplhf | leftEye / rightEye |
| L/R collar | L/R shoulder |
| L/R shoulder / elbow / wrist | L/R upperArm / lowerArm / hand |
| L/R hip / knee / ankle / foot | L/R upperLeg / lowerLeg / foot / toes |
| thumb1-3 | ThumbMetacarpal / ThumbProximal / ThumbDistal |
| index/middle/ring/pinky 1-3 | Proximal / Intermediate / Distal |

Mixamo 命名（[[Make-It-Animatable]] 輸出）也可用 [[VRM Add-on for Blender]] 的 `assign_vrm1_humanoid_human_bones_automatically` 自動對應。
