# Single-Photo-VRM 實作規劃

> 依據：[RESEARCH.md](RESEARCH.md)（2026-09-29 調研，全部一手來源查證）

## 目標

一張照片 → 自動產出 **VRM（0.x + 1.0）**，具備：
1. **標準 humanoid 骨架**（含手指），可直接吃 Mixamo / VRMA 動作
2. **Perfect Sync 臉**：ARKit 52 blendshapes（含嘴形、`tongueOut`、`eyeLook*`），iPhone Face ID Cam（iFacialMocap / Waidayo）→ VSeeFace / Warudo 一對一驅動
3. VRM 標準表情 preset（aa/ih/ou/ee/oh、blink、happy…）由 ARKit 組合生成，非 Perfect Sync 的 app 也能用
4. 全程 headless、可腳本化，不需開 Unity

**品質對照組**：VTubeMe（$7.99，MetaPerson 系，54 骨 / 66 morph）。

## 核心架構：「重建身體 + 範本頭」

調研結論：沒有開源模型能一步到位；而且任何單圖重建出的頭都是封閉表面（沒眼球、沒口腔），**Perfect Sync 在物理上做不出來**。所以臉部不重建，改用帶完整表情 rig 的範本頭擬合照片。

```
                    ┌─────────────── 臉 (Mac 可跑) ───────────────┐
照片 ─┬─ 臉部裁切 ─→ MediaPipe landmarks ─→ 擬合 ICT-FaceKit identity
      │                                  ─→ 照片投影到 ICT UV + inpaint
      │                                  ─→ ICT 52 表情 delta（+自製 tongueOut）
      │                                     眼球 / 牙齒 / 舌頭 / 口腔 內建
      │                                              │
      └─ 全身 ─→ (可選) 正規化成正面 A-pose           │
               ─→ PSHuman: 有貼圖 mesh + 對齊 SMPL-X  │  (CUDA GPU)
               ─→ SMPL-X 權重轉移 + unpose 成 T-pose  │
               ─→ 切頭 ←──────── 頸部接合 ────────────┘
                              │
                     Blender (bpy-vrm-format, headless)
                     ├─ SMPL-X joint → VRM humanoid（1:1 含手指）
                     ├─ 52 morph (lowerCamel) + VRM0 clip (PascalCase)
                     ├─ preset 表情、eye bone + lookAt、MToon、meta
                     └─ 匯出 VRM0 + VRM1
                              │
               vrm-validator + three-vrm 預覽 + iPhone 實測
```

**為什麼不用 Grok 的 LHM → Mesh2Motion**：LHM 輸出是 Gaussian 不是 mesh；Mesh2Motion 純 GUI 無法自動化；再綁一次骨等於丟掉 SMPL-X 已有的骨架與權重；且兩者都不處理臉。

## 開發階段（先打通尾端，再往前推）

### Phase 0 — 匯出與驗證骨架（Mac，無 GPU）
- [ ] 建 Python 環境，`pip install bpy-vrm-format`，實跑一次 headless 匯出（API 名稱只對過原始碼、未實跑）
- [ ] 拿 hinzka 的 Perfect Sync VRoid VRM 做 round-trip（讀入 → 匯出 VRM0 + VRM1），確認 52 clip / morph 名稱保留
- [ ] `vrm-validator` CLI 接進流程
- [ ] three-vrm 預覽頁：52 個 ARKit slider + VRMA 播放 + Playwright 自動截圖
- [ ] **實機驗收**：iPhone iFacialMocap → VSeeFace（VRM0）與 Warudo 驅動 round-trip 後的檔案

**完成標準**：一個已知的 Perfect Sync VRM 經我們的匯出器後，在 VSeeFace 用 iPhone 能正常驅動嘴形、眨眼、眼球、舌頭。

### Phase 1 — ICT 範本頭 → Perfect Sync VRM（Mac）
- [ ] 下載 ICT-FaceKit，把平均臉 + 眼球 + 牙齒 + 舌頭組成單一頭部
- [ ] 51 個 ARKit shape 改名（合併 `browInnerUp`、`cheekPuff` 的 L/R），手雕一次 `tongueOut`
- [ ] 頭 + 最小身體（SMPL-X 中性身體或 VRoid base）→ VRM
- [ ] 眼骨 + lookAt；由 ARKit 組合出 VRM preset 表情

**完成標準**：「無照片」的 ICT 平均臉 VRM，用 iPhone 驅動的效果達到 Phase 0 的水準。

### Phase 2 — 照片 → 擬合臉（Mac，MediaPipe 可在 CPU 跑）
- [ ] MediaPipe Face Landmarker → 對 ICT 100 個 PCA identity mode 做 landmark + photometric 優化
- [ ] 照片投影到 ICT UV，被遮住的區域 inpaint，再做膚色 albedo 化（去光照）
- [ ] 評估：用同一個人的多張照片檢查擬合穩定度；和 VTubeMe 做並排比較

### Phase 3 — 身體（CUDA GPU：Nebius / Brev H100）
- [ ] PSHuman（>40 GB VRAM，`with_smpl=true`）跑出有貼圖 mesh + SMPL-X
- [ ] 最近點轉移 SMPL-X LBS 權重，再做 inverse LBS 把 mesh unpose 成 T-pose
- [ ] 實驗：先用圖像編輯模型把輸入照片正規化成正面 A-pose，看能不能減少 unpose 在腋下、胯下的破面（假設，待驗證）
- [ ] 頸部接合：切掉重建頭部 → RBF/Laplacian 混合 → UV 空間融膚色
- [ ] 對照實驗：LHM++ canonical T-pose Gaussian → 多視角渲染 → 轉 mesh（權重 NC，僅供研究比較）

### Phase 4 — 二次元路線（Mac）
- [ ] hinzka Perfect Sync VRoid base + blender-vrm-perfect-sync
- [ ] 照片 → VLM 判斷髮型、髮色、瞳色、膚色、服裝 → 從零件庫挑選、調色；臉部貼圖做風格化 img2img
- [ ] 進階：StdGEN 生成的分層頭髮 / 服裝 → 掛到 VRoid base，頭髮自動加 spring bone
- 這條路是調研中發現**還沒人做**的空缺，而且保證輸出合格 VRM

### Phase 5 — 動作與產品化
- [ ] VRMA：bvh2vrma、Mixamo FBX → VRMA、HY-Motion → Blender retarget → VRMA
- [ ] Web 前端：上傳照片 → 預覽 → 下載 VRM0/VRM1
- [ ] 選項：iPhone 直連網頁預覽（Node 版 VMC/iFacialMocap UDP bridge → WebSocket → three-vrm）

## 硬體分工

| 階段 | 位置 |
|---|---|
| Phase 0 / 1 / 2 / 4、Blender 匯出、驗證 | M4 Max 本機 |
| Phase 3 身體重建（PSHuman >40 GB） | Nebius / Brev H100 |

## 授權（上線前必須決定）

| 用途 | 身體 | 臉 |
|---|---|---|
| 研究 / 個人 | PSHuman + SMPL-X（非商用）即可 | ICT（MIT） |
| **商用** | SMPL-X 需向 Meshcapade 買授權；或改用 TRELLIS.2（MIT）+ MIA v1（MIT/Apache，Mixamo 骨架）| ICT（MIT）+ 自寫擬合；**避開** DECA/EMOCA/MICA/FreeUV/BFM |

二次元路線（hinzka + VRM Add-on + StdGEN）可商用。

## 待決定事項
1. **優先做寫實還是二次元？**（建議：Phase 0 → 1 兩條路共用，之後再分岔）
2. **會不會商用？** 這決定身體要用 SMPL-X 還是 MIT 替代方案。
3. 手上有沒有 iPhone + iFacialMocap / Waidayo 可以做實機驗收？
