---
type: concept
verified: 2026-09-29
tags:
  - concept
  - ai
  - mlx
---
# AI Turnaround

選用功能：`photo2vrm --ai-turnaround`（或測試台「進階設定 → AI 三視圖」）。程式：`template/fit/multiview.py`、`fit/texture.py:bake_multiview`。

## 模型
- **FLUX.2-klein-4B**（Black Forest Labs，**Apache-2.0**，Hugging Face 未 gated）
- 執行：[[mflux]]（MLX，Apple Silicon GPU / Metal），獨立 venv `template/.venv-mflux`
- 權重約 15 GB，放在 `~/.cache/huggingface`；`--quantize 8` 載入
- M4 Max：4 步 × ~10.6 s ≈ 42 s，MLX 峰值 23 GB

## 流程
1. 去背照片合成白底 → `mflux-generate-flux2-edit` 1536×1024，提示：遊戲設計三視圖（正 / 側 profile facing left / 背）、去眼鏡與臉部飾品、T-pose、白底、同一人同服裝
2. 分割：白底差異 + MediaPipe 人像分割 → GrabCut → 取三大連通區，依 x 排序；三張用**同一個縮放**（出自同一張圖 → 同一像素尺度），腳底對齊
3. 側面朝向：MediaPipe 鼻子在耳朵左 / 右 → yaw −90° / +90°
4. 擬合：共用 Anny 體型 + 身體姿勢 + 相機尺度；每視角位移 + 手臂（鎖骨 / 上臂 / 前臂）微調；正面用骨架點；三視角輪廓在內 + 覆蓋（1.5% 身高的衣物容許）
5. 貼圖（臉部預設取自**原始照片**：額外的「照片視角」只用在頭骨正面三角形並加分優先；`--face-texture ai` 改用 AI 正面去除眼鏡）：每個 texel 在三視角中選最正對、未遮擋、在輪廓內的像素；手只取皮膚、軀幹 / 腿不取皮膚；頭部以 AI 正面的臉部點做 affine 對齊
6. 髮型：背面垂過脖子 → 馬尾（窄）/ 長髮（寬）；側面後腦凸出 > 0.12 頭寬 → 髮髻

## 實測（2026-09-29）
- T-pose 女性：三視圖一致，背面看出**低髮髻** → 自動選髮髻；側面朝左正確
- 插腰西裝男：AI 正面把手放下（A-pose）→ 正面不再有腰上的手；背面是真的西裝背面
- 坑：AI 三視圖的手臂在正面 / 側面不一致 → 需每視角手臂微調；寬鬆衣物會把身體撐胖 → 覆蓋容許
- 坑：改了 `server.py` 要重啟 API，否則跑的是舊程式（曾因此跑成「只生成背面」）
