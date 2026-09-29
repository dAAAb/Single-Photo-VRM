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

## 知識庫

`kb/` 是 Obsidian vault（用「Open folder as vault」開啟 `kb/`），從 `kb/00-MOC/Home.md` 開始：

- `kb/00-MOC/Implementation Plan.md`：架構與開發階段
- `kb/00-MOC/Research Survey.md`：完整調研（2026-09-29，一手來源查證）

## Status

- ✅ Phase 0a：VRM Test Bench
- 🚧 Phase 0b：範本 VRM（Anny 身體 + ICT-FaceKit 頭）
