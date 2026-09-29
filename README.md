# Single-Photo-VRM

從單張照片自動生成 VRM 虛擬角色：標準 humanoid 骨架（可吃 Mixamo / VRMA 動作）＋ **Perfect Sync（ARKit 52 臉部表情，iPhone Face ID Cam 相容）**。Web 優先、不需 CUDA。

## VRM Test Bench

拖進任何 `.vrm` 就能測動作、表情和相容性：

```bash
cd viewer && npm install && npm run dev   # → http://localhost:5188
```

- **WASD** 移動 · **Shift** 跑 · **空白鍵** 跳，鏡頭跟隨
- 拖放 `.vrma` 或 Mixamo `.fbx`，可指定為 待機 / 走 / 跑 / 跳
- VRM 表情和 Perfect Sync 52 滑桿；**Webcam 即時驅動**（MediaPipe，全部在瀏覽器內處理）
- 相容性檢查：必要骨、手指、preset、52 ARKit 分別對 VSeeFace（VRM0 PascalCase）和 Warudo（lowerCamel morph）檢查

## 照片 → VRM

```bash
template/build.sh                                   # 一次性：Python 環境、VRM Add-on、模型
template/.venv/bin/python template/photo2vrm.py photo.png   # CLI → build/out/photo.vrm0.vrm / .vrm1.vrm
template/.venv/bin/python template/server.py        # 或：啟動本機 API，再到 Test Bench「生成」頁籤拖入照片
```

任何人形照片（T-pose 或任意姿勢、真人或卡通）→ 去背置中 → 身形 + 臉型擬合 → 貼圖 → T-pose Perfect Sync VRM。加 `--ai-backview` 可用 FLUX.2-klein-4B 生成背面（選用，首次下載約 15 GB）。Mac CPU 約 35–60 秒，不需 CUDA。

## 知識庫

`kb/` 是 Obsidian vault（用「Open folder as vault」開啟 `kb/`），從 `kb/00-MOC/Home.md` 開始：

- `kb/00-MOC/Implementation Plan.md`：架構與開發階段
- `kb/00-MOC/Research Survey.md`：完整調研（2026-09-29，一手來源查證）

## Status

- ✅ Phase 0a：VRM Test Bench
- ✅ Phase 0b：範本 VRM（Anny：身體 + ARKit 52 臉 + 舌頭 + 牙齒）
- ✅ Phase 1：Perfect Sync 實機驗收（webcam / iPhone + VSeeFace）
- ✅ Phase 2：照片 → 身形 + 臉型擬合（Python 原型，拖放介面）
- ✅ Phase 3：貼圖（照片投影；選用 AI 背面 FLUX.2-klein-4B）
