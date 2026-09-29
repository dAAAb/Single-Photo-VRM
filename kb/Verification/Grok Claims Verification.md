---
type: verification
verified: 2026-09-29
tags:
  - verification
  - grok
---
起點：使用者詢問 Grok 的回答（LHM + Mesh2Motion + UniVRM）。逐項以一手來源查證。

| Grok 說法 | 判定 | 筆記 |
|---|---|---|
| LHM 可經 `inference_mesh.sh` 導 mesh | ❌ **誤導**：實際輸出 Gaussian .ply | [[LHM]] |
| LHM++ 0.79 s、3DGS .ply | ✅（但權重 CC BY-NC）| [[LHM++]] |
| IDOL CVPR'25 | ✅（無 LICENSE 檔）| [[IDOL]] |
| HumanLift SIGGRAPH Asia'25 | ✅（需手動 Photoshop）| [[HumanLift]] |
| GeneMAN NeurIPS'25 | ✅ | [[GeneMAN]] |
| DiGS-Avatar 2026 | ✅ | [[DiGS-Avatar]] |
| PERSONA 2026 | ❌ **實為 ICCV 2025** | [[PERSONA]] |
| UniRig + HF 權重 + MIA 人型路徑 | ⚠️ 大致對；VRoid ckpt pending、骨架非 humanoid、MIA 在 GPL 的 ComfyUI 節點 | [[UniRig]] |
| Mesh2Motion v13、可離線、MIT | ✅（離線是 Update 12 desktop app；純 GUI）| [[Mesh2Motion]] |
| AccuRIG 免費非開源 | ✅ | [[Other Auto-Riggers]] |
| HY-Motion 1.0 2025-12、1B DiT | ✅ | [[HY-Motion 1.0]] |
| text-to-vrma | ✅ | [[VRMA Tools]] |
| MotionMind | ✅ 存在但玩具級 | [[VRMA Tools]] |
| 「UniVRM 仍是最穩的一環」 | ⚠️ 已可完全不用 Unity | [[VRM Add-on for Blender]] |

## 結構性問題
1. LHM →（抽 mesh）→ Mesh2Motion 重新綁骨 = **丟掉已有的 SMPL-X 骨架與權重** → 應用 [[SMPL-X Weight Transfer]]
2. **完全沒處理臉部表情** → [[Perfect Sync]]
3. 未提授權風險 → [[Licensing Matrix]]
4. 未提 CUDA 限制 → [[Hardware Split]]
