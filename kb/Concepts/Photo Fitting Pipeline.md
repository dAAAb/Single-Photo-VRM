---
type: concept
verified: 2026-09-29
tags:
  - concept
  - fitting
  - pipeline
---
# Photo Fitting Pipeline

`template/photo2vrm.py`（Python 原型；Mac CPU，不需 CUDA）。**所有規則都是通用的，沒有針對特定測試圖寫死**；`test_images/` 只是回歸測試集。

| 步驟 | 模組 | 做法 |
|---|---|---|
| 1 去背 / 置中 | `fit/preprocess.py` | 真 alpha 優先；否則 MediaPipe **多類別人像分割**（uint8 category mask）+ 姿勢骨架線 + 邊框顏色 k-means → GrabCut；最大連通區 + 補洞；置中成 1024² |
| 2 偵測 | 同上 | Pose Landmarker heavy（21 點 → Anny COCO 標籤）；Face Landmarker 在放大的頭部裁切上跑（478 點 + blendshape） |
| 3 身體 | `fit/body.py` | Anny（6 phenotype + 23 身形 local change）+ 17 骨 local-ref 姿勢 + 正交相機；損失 = GMoF 關鍵點 + 輪廓在內（背景距離場）+ 輪廓覆蓋（chamfer）；Adam 兩階段約 15 秒 |
| 4 臉 | `fit/face.py`、`fit/face_corr.py` | 見下 |
| 4.5 貼圖 | `fit/texture.py`（+ 選用 `fit/backview.py`） | UV texel → 照片姿勢網格 → 投影取色；可見 / 同部位正面延伸 / 後腦髮色 / inpaint；頭部 478 點 affine 對齊；選用 FLUX.2-klein-4B 背面 |
| 5 匯出 | `export_anny.py --params` | 同一組參數 → T-pose；風格化骨頭縮放在 T-pose 空間烘焙（頂點 / 骨頭 / 52 表情差值都一起變換） |
| 6 VRM | `build_vrm.py`（Blender headless） | 同 [[VRM Test Bench]] 驗證過的範本流程 |

## 自動模式判斷
- **寫實**（預設）
- **風格化**：`臉寬 / 身高 > 0.15`（真人 0.08–0.09；Mario 0.19）。改用輪廓主導、骨頭縮放（頭 / 手腕 / 腳 / 大腿 / 小腿 / spine03）、形狀外插；輪廓是 T-pose 時固定標準 T-pose，逼形狀去解釋輪廓
- ⚠️ 不要用「擬合誤差大」判斷卡通：寬鬆長袍也會造成誤差大（實測誤判過）

## 臉部對應（免人工標註）
1. numpy 光柵器正面渲染 Anny 中性臉（膚色、虹膜、瞳孔）+ 三角形 ID buffer
2. 在渲染圖上跑 MediaPipe → 478 點
3. 每點查三角形 + 重心座標 → `build/models/mp478_anny.npz`

擬合：約 110 個臉部 local change（鼻、口、下巴、額、眉、眼、頰；**耳朵排除**，MediaPipe 看不到）+ 頭部剛體 + 尺度；2D + 弱 z 損失；照片表情由 MediaPipe blendshape 設為 Anny facial action（同名 ARKit）固定；左右對稱先驗。

## 踩坑
- **MediaPipe 1.0.1（macOS wheel）**：偵測器初始化 Metal 直接 abort（`Service is unavailable`），指定 CPU delegate 也一樣 → 用 **0.10.35**
- **MediaPipe 0.10.35**：float 遮罩 `numpy_view()` abort（`1 == ChannelSize()`）→ 只用 uint8 category mask
- 2026-09-29 下午量到的 ~100 KB/s 是暫時的網路狀況（晚上 HF 14.7 MB/s）→ 大型下載前先實測，不要憑單次測量下結論
- 網路慢時 `rembg`（numba / llvmlite）+ BiRefNet 太重 → Python 版不用；Web 版再用 BiRefNet（transformers.js）
- 性別從單張輪廓判斷不可靠（多起點比較還會選錯）→ 使用者提示 / 之後 VLM
- GMoF 覆蓋損失的 σ 太小時，遠處的輪廓（卡通大頭）梯度為零 → 風格化模式用由粗到細的 σ

## 結果（2026-09-29，9 張測試圖）
- 全部產出 VRM，檢查台 Perfect Sync 52/52
- 寫實：站、坐、蹲、跳、插腰都能擬合；長袍抬腿那條腿被袍子遮住（MediaPipe 本身標錯）
- 卡通 Mario：大頭 1.7×、短腿、T-pose；但身體是裸體 → 吊帶褲體積要靠貼圖 / 服裝層
- 已知不足：豐腴體型被低估；灰模看不出像不像 → 下一步貼圖（Phase 3）
