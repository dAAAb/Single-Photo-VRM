---
type: concept
verified: 2026-09-29
tags:
  - concept
  - architecture
  - infra
---
| 層 | 環境 | 內容 |
|---|---|---|
| **T0 Web** | WebGPU / WebGL2 / WASM | [[Template Morphing]] 全流程；webcam [[Perfect Sync]] 預覽 |
| **T1 本地加值** | Mac MLX / MPS / Core ML；Win/Linux MLX-CUDA、PyTorch | [[mflux]] 正面 A-pose / 背面視角；Depth Anything V2 Small（Apple 官方 Core ML 版）；[[oMLX]] VLM；[[Mac Image-to-3D Ports]]（實驗）|
| **T2 CUDA** | Nebius / Brev / NVIDIA | [[PSHuman]]、[[LHM]] 衣服幾何；加速 T1 |

## WebGPU 支援（2026-09，gpuweb wiki）
| 瀏覽器 | 狀態 |
|---|---|
| Chrome / Edge 桌面 | ✓（113+）|
| Chrome Android 12+ | ✓（121+）|
| Chrome Linux | Intel Gen12+（144）、NVIDIA / Wayland（147）；Windows ARM64 需開 flag |
| Safari 26（macOS / iOS / iPadOS / visionOS）| ✓ 預設開啟 |
| Firefox Windows | ✓（141+）|
| Firefox macOS | Apple Silicon（145+）|
| Firefox Linux / Android | 僅 Nightly |

→ 永遠保留 WASM / WebGL fallback。

## 跨平台
- **共用核心 = TypeScript**（擬合、GLB patch、投影）：瀏覽器 / Node / Tauri 通用
- **MLX 已跨平台**：`mlx` 0.32.3 有 macOS arm64、Linux、Windows wheel；`mlx[cuda12|13]`（Linux + win_amd64）；`mlx-cpu`。但 mflux 能不能跑在 MLX-CUDA 上**未驗證** → CUDA 路徑保留 diffusers / PyTorch
- PyTorch 選 device 的順序：cuda → mps → cpu，加 `PYTORCH_ENABLE_MPS_FALLBACK=1`
- **bpy 5.2.2** 三平台都有 wheel，但**只支援 Python 3.13** → Blender 跑在獨立 process（`blender -b --python`），而且只在開發時用來做範本
- 桌面版：Tauri v2 + PyInstaller sidecar（`bundle.externalBin`，依 target triple 命名）

## Mac 和 CUDA 的速度差
| 項目 | Mac | CUDA |
|---|---|---|
| LiTo | ~160 s | ~4.6 s |
| TRELLIS.2 | 5–9 min | ~17 s |
| Qwen-Edit 20B | 數分鐘 | — |
| 擬合 / MediaPipe / patch | 秒以內 | 秒以內 |
