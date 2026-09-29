---
type: tool
stage: enhance
license_code: "見內文"
license_weights: "見內文"
commercial: "見內文"
last_update: 2026-09-29
verified: 2026-09-29
tags:
  - tool
  - local
  - mac
  - image-to-3d
---
| 專案 | Mac 路徑 | 速度 | 授權 | 輸出 |
|---|---|---|---|---|
| Apple LiTo（ml-lito）| 官方 MLX | M4 Max ~160 s（H100 ~4.6 s）| Apple sample code + 權重另有條款 | PLY |
| Apple SHARP（ml-sharp）| CPU / MPS | GPU 上 <1 s | **僅限研究** | 場景 3DGS |
| [[TRELLIS.2]] → trellis-mac | MPS + Metal kernel | M4 Pro ~5 min；**連續跑會過熱降速**（3.5→36 min）| MIT（但 RMBG-2.0 NC、DINOv3 需申請）| GLB |
| TRELLIS.2 → trellis2mlx | 純 MLX | M4 Max 6–9 min | 無授權、實驗性 | GLB |
| Hunyuan3D-2.1 官方 | 支援 macOS | 形狀 10 GB / 貼圖 21 GB | Tencent 社群授權 | GLB PBR |
| Hunyuan3D-MLX（Swift）| MLX | 形狀 ~21 s；PBR ~344 s（~39 GB）| MIT wrapper | GLB |
| SAM 3D Objects / Body | CUDA 寫死（issue #32 未解）| — | SAM License | — |
| LHM / PSHuman / SiTH / ECON | **沒有 Mac 版** | — | — | — |

結論：人體專用的重建模型都沒有 Mac 版；通用 image-to-3D 在 Mac 上一件要好幾分鐘 → 只當 T1 實驗性加值，不放在主線（見 [[Template Morphing]]）。
