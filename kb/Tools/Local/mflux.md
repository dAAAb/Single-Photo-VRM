---
type: tool
stage: enhance
url: https://github.com/filipstrand/mflux
license_code: "MIT"
license_weights: "見內文"
commercial: "見內文"
last_update: 2026-09-21 v0.20.0
verified: 2026-09-29
tags:
  - tool
  - local
  - mlx
  - mac
  - image-edit
  - recommended
---
MLX 原生的圖像生成 / 編輯工具。[[Platform Tiers]] T1 的核心。

| 模型 | 用途 | 授權 |
|---|---|---|
| **Qwen-Image-Edit-2511**（預設編輯模型；2509 multi-angle LoRA 可用）| 照片轉正面 A-pose、**生成背面視角** | Apache ✓ |
| **FLUX.2-klein-4B** | 多張參考圖編輯 | Apache ✓ |
| Z-Image-Turbo | 生成 | Apache ✓ |
| FLUX.1 Fill | 補洞 | 查 |
| FLUX.1 Kontext-dev / FLUX.2-klein-9B | 編輯 | BFL 非商用 ✗ |

速度（第三方數據，未驗證）：klein-4B 1024px 4 步 ≈ M1 Max 30–40 s；Qwen-Edit（20B）要好幾分鐘，除非用 Lightning LoRA。
CUDA 上改用 diffusers 跑**同一份權重**。其他：DiffusionKit 已停更（2025-04）；ComfyUI（GPL）支援 MPS。
