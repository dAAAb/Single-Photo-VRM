---
type: tool
stage: face
license_code: "見內文"
license_weights: "—"
commercial: "—"
last_update: 2026-09-29
verified: 2026-09-29
tags:
  - tool
  - face
  - arkit
---
任意頭 mesh 自動產生 52 shapes（備案；主線用 [[ICT-FaceKit]] 拓樸不需要）：

  | 工具 | 授權 | headless |
  |---|---|---|
  | [deformation_transfer_ARkit_blendshapes](https://github.com/vasiliskatr/deformation_transfer_ARkit_blendshapes) | MIT | ✓ Python，需對應點 |
  | QtMeshEditor（issue #889） | MIT | ✓ CLI；ICT 尺寸頭 51 shapes 已報告驗證 |
  | [NFR](https://github.com/dafei-qin/NFR_pytorch) | MIT | 部分（demo 需顯示器）；映射到 ICT FACS |
  | NVIDIA Audio2Face-3D | SDK MIT / NVIDIA Open Model | ✓；**產生動畫，不是 shape** |
  | Faceit / Polywink / HANA_Tool | 商用 | ✗ |
  | RigAnyFace（NeurIPS'25）、OmniFaceRig（2606.08043）、TopoRig（2609.15746） | — | 無程式碼 |

  VRM 端：VRM Add-on 的 `vrm.assign_vrm1_expressions_from_arkit` 可一鍵把 ARKit shape key 建成 VRM1 custom expression（見 [[VRM Add-on for Blender]]）。
