---
type: tool
stage: perception
url: https://github.com/huggingface/transformers.js
license_code: "MIT / Apache-2.0"
license_weights: "見內文"
commercial: "見內文"
last_update: 2026-09
verified: 2026-09-29
tags:
  - tool
  - web
  - web
  - webgpu
---
- onnxruntime-web 1.30.0（2026-09-10）+ WebGPU Plugin EP v0.4.0
- transformers.js 4.0.0（2026-03-30，新的 C++ WebGPU runtime）→ 4.3.0；瀏覽器 / Node / Bun / Deno 都能跑

| 模型 | 瀏覽器 | 授權 | 商用 |
|---|---|---|---|
| Depth Anything V2 **Small** | ✓ | Apache | ✓（Base 以上 CC-BY-NC ✗）|
| LaMa（Carve/LaMa-ONNX，208 MB）| ✓ | Apache | ✓ |
| BiRefNet(_lite) | ✓ | MIT | ✓ |
| MI-GAN | ✓ | MIT？（issue #25 質疑衍生自 NVIDIA-NC）| ⚠️ |
| RMBG-1.4 / 2.0 | ✓ | BRIA 非商用 | ✗ |
| Sapiens normal | ONNX 有 | CC-BY-NC | ✗ |
| DSINE | ✗ | Imperial 自訂 | ✗ |
| face-parsing（CelebAMask-HQ）| ✓ | 無 / 非商用資料 | ⚠️ |

→ 髮 / 膚 / 衣分割用 [[MediaPipe Tasks Vision]] 最安全；法線從深度推。
