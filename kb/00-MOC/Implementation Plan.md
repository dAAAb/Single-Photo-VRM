---
type: plan
version: 2
updated: 2026-09-29
tags:
  - plan
---
# Single-Photo-VRM 實作規劃 v2：Web 優先、不需 CUDA

> v1（CUDA 身體重建優先）見 git history `77f1adb`。依據：[[Research Survey]]、[[Platform Tiers]]。

## 目標

一張照片 → 自動產出 **VRM（0.x + 1.0）**：
1. 標準 humanoid 骨架（含手指）
2. **[[Perfect Sync]]**：ARKit 52 blendshapes（含嘴形、`tongueOut`、`eyeLook*`），支援 iPhone Face ID Cam 驅動
3. 先在 **Mac 本地 / 瀏覽器跑，不需 CUDA**；Windows / Linux / Web 跨平台；最後才接 CUDA 加速

## 核心轉向：[[Template Morphing]]

不在執行時「生成」3D，而是改寫一個事先做好的範本：

```
開發時（一次性，Blender）
  Anny 身體 (CC0) + ICT-FaceKit 頭 (MIT) → 接合好的 template.vrm
  ├─ humanoid 骨架、eye bones、lookAt
  ├─ 52 ARKit morph（lowerCamel）+ VRM0 PascalCase clip + VRM preset
  └─ MToon、spring bone、meta

執行時（每張照片，瀏覽器內）
  照片 → MediaPipe（478 臉點 / 33 身體點 / 髮-膚-衣分割）
       → JS 最小平方擬合：ICT 100 identity 係數 + Anny 身材參數
       → 直接 patch GLB：頂點 / 骨頭位置 / inverseBindMatrices（morph delta 不動）
       → 照片投影到 UV + LaMa 補洞 + 膚色 / 髮色
       → 下載 VRM0 + VRM1
```

**為什麼可行**：ICT 和 Anny 都是線性模型；表情 morph 本來就是差值，跟臉型無關 → 換臉型時 52 個表情不必重算。頭身接縫也只要在範本裡做一次（見 [[Head-Body Stitching]]）。擬合只是約 1434 個殘差 × 107 個未知數的最小平方問題，純 JS 幾十 ms 就能解（估計值）。

## 三層架構（[[Platform Tiers]]）

| 層 | 環境 | 做什麼 | 狀態 |
|---|---|---|---|
| **T0 Web** | 瀏覽器 WebGPU / WebGL / WASM（Chrome、Edge、Safari 26；Firefox 部分支援）| 完整 pipeline 的基本版 + webcam Perfect Sync 預覽 | **第一個做** |
| **T1 本地加值** | Mac：MLX / MPS / Core ML；Win/Linux：MLX-CUDA / PyTorch | [[mflux]] 生成正面 A-pose 和背面視角 → 更完整的貼圖；Depth Anything；[[oMLX]] 跑 VLM 判斷屬性、當品質評審；（實驗）Mac 版 Hunyuan3D / TRELLIS.2 做衣服幾何 | 第二個做 |
| **T2 CUDA** | Nebius / Brev / 本機 NVIDIA | [[PSHuman]] / [[LHM]] 做高擬真衣服幾何、加速 T1 | 最後做 |

共用核心 = **TypeScript 函式庫**（擬合、GLB patch、貼圖投影），瀏覽器 / Node / Tauri 通用。Python 只在 T1/T2 當 sidecar。桌面版用 Tauri v2 + PyInstaller sidecar 打包三平台。

## 開發階段

### Phase 0a — VRM 測試頁（[[VRM Test Bench]]）✅ 先做
瀏覽器測試台，**所有後續階段都用它驗收**，也能測任何現有 VRM：
- [x] 拖放 `.vrm`（0.x / 1.0）；顯示 meta
- [x] 相容性檢查：15 根必要骨、手指、選配骨、VRM preset、ARKit 52（分別檢查 VSeeFace 的 PascalCase clip 和 Warudo 的 lowerCamel mesh morph）、lookAt、spring bone、firstPerson
- [x] **WASD 移動 / Shift 跑 / 空白鍵 跳**，第三人稱鏡頭；內建程序式 待機 / 走 / 跑 / 跳（不需動畫檔）
- [x] 拖放 `.vrma` 或 Mixamo `.fbx` → 播放，或指定到 待機 / 走 / 跑 / 跳 取代內建動作
- [x] VRM 表情滑桿、Perfect Sync 52 滑桿（缺的標紅）
- [x] Webcam：MediaPipe 追蹤臉 → 即時驅動 52 表情 + 頭部轉動（沒 Perfect Sync 的模型用 preset 近似）
- [x] 視線跟隨、spring bone 開關、截圖

### Phase 0b — 範本 VRM（Mac，Blender，一次性）✅ 基本版完成

> [!success] Spike 結論（2026-09-29）：**只用 Anny，不接 ICT 頭**
> Anny v0.6 的 `facial_actions` 剛好就是 **ARKit 52 個名稱**（Face Units，CC0），而且網格裡有**獨立的舌頭（226 頂點）和左右眼球**，還有 `eye.L/R` 眼骨。`tongueOut` 只會動舌頭。唯一缺的是牙齒。
> → 省掉頭身接合，全線 Apache + CC0。見 [[Anny]]。

產出：`template/build.sh` → `build/template.vrm1.vrm`、`build/template.vrm0.vrm`
- [x] Anny → T-pose（world-orient 參數化，手臂 ±X、腿垂直）、腳底平移到 y=0
- [x] 52 ARKit shape key（lowerCamel）+ VRM1 custom expression + VRM0 PascalCase clip
- [x] VRM preset（aa/ih/ou/ee/oh、blink、happy/angry/sad/relaxed/surprised）由 ARKit 組合
- [x] humanoid 對應：15 必要骨 + 30 手指骨 + 肩、胸、頸、眼；lookAt = 眼骨
- [x] 材質：膚色、舌頭、眼睛（鞏膜 / 虹膜 / 瞳孔依幾何切分）
- [x] Khronos glTF validator：VRM1 0 錯誤 0 警告；VRM0 0 錯誤（1 個 VRM0 擴充命名的固有警告）
- [x] [[VRM Test Bench]]：VRM0 在 VSeeFace 52/52、Warudo 52/52、lookAt 骨頭型；走 / 跑 / 表情都正常
- [x] 牙齒：`anny-full` 拓樸保留 MakeHuman 的 `helper-upper/lower-teeth`（CC0），Face Units 本來就會讓**下排牙跟著 jawOpen / jawLeft / jawRight / jawForward 動**，上排固定
- [x] Phase 1 實機驗收（使用者，2026-09-29）：webcam 眨眼、張嘴、左右方向正確；Perfect Sync 可驅動
- [ ] 皮膚 / 眼睛貼圖（目前是純色）
- [ ] 頭髮（零件庫，見 Phase 5）
- [ ] 檔案大小：52 個 morph 各存完整頂點 → 約 19 MB；改用 sparse accessor
- [ ] mrxz/vrm-validator（需要 Dart SDK，還沒跑）

<details><summary>原本的 Phase 0b 待辦（已被 spike 取代）</summary>

- [ ] 裝 Anny（`naver/anny`），匯出中性身體 + rig（104 骨 anny rig → 對 VRM humanoid）
- [ ] ICT-FaceKit 頭：51 shape 改名（合併 L/R）+ 手雕 `tongueOut` → ARKit 52
- [ ] **Spike：** 比較 Anny / MPFB 自帶的 Face Units（CC0，傳聞有 54 個 ARKit shape，未驗證）和 ICT。如果 Anny 的臉夠用，就不必接頭，但臉型擬合的自由度會比較低
- [ ] 頭身接合 + 頸部權重 → 用 [[VRM Add-on for Blender]] 匯出 `template.vrm`（VRM0 + VRM1）
- [ ] [[vrm-validator]] 通過；在 [[VRM Test Bench]] 全部檢查為綠燈
</details>

### Phase 1 — Perfect Sync 驗收
- [ ] 在 [[VRM Test Bench]] 用 webcam 驅動範本 VRM 的 52 個 morph
- [ ] 實機驗收：iPhone iFacialMocap → VSeeFace（VRM0）/ Warudo

**完成標準**：範本 VRM 在瀏覽器 webcam 和 VSeeFace + iPhone 兩邊都能正確驅動嘴形、眨眼、眼球、舌頭。

### Phase 2 — 照片 → 身形 + 臉型擬合 ✅ Python 原型（Mac，不需 CUDA）

> 先用 Python（Anny 目前只有 PyTorch 版）驗證方法，再移植到 Web。見 [[Photo Fitting Pipeline]]。

入口：`template/photo2vrm.py <任意人形照片>` → `build/out/<name>.vrm0.vrm / .vrm1.vrm`（約 35–60 秒）；
介面：[[VRM Test Bench]] 的「生成」頁籤，拖入照片 → 本機 API（`template/server.py`）→ 自動載入 VRM。

- [x] 去背 + 置中：真 alpha 優先；否則 MediaPipe 多類別人像分割 + 姿勢骨架 + 邊框色模型 → GrabCut
- [x] 偵測：MediaPipe Pose（21 點）+ Face Landmarker（478 點 + 51 blendshape），臉部用放大的頭部裁切
- [x] 身體擬合：Anny 6 phenotype + 23 個身形 local change + 17 根骨頭的姿勢（只用來解釋照片，輸出一律 T-pose）+ 正交相機；關鍵點 + 輪廓（在內 / 覆蓋）
- [x] **非 T-pose**：坐、蹲、跳、插腰都能擬合；姿勢被丟掉，輸出 T-pose
- [x] **卡通 / 風格化模式**：臉寬 / 身高 > 0.15 時啟用（真人 ≈ 0.08，Mario 0.19）；骨頭縮放（頭、手、腳、腿、胸）+ 形狀外插；T-pose 輪廓時固定標準 T-pose
- [x] 臉型擬合：MediaPipe 478 ↔ Anny 對應**自動建立**（渲染 Anny 臉 → 跑 MediaPipe → 三角形 + 重心座標）；約 110 個臉部 local change + 頭部剛體；照片表情用 MediaPipe blendshape 當 Anny facial action 固定，不會把笑容擬合成臉型；左右對稱先驗
- [x] 回歸測試：`template/run_suite.sh` 跑 `test_images/` 全部 + `build/qa_sheet.png`（9 張全過）
- [ ] 性別：單張輪廓無法可靠判斷 → 目前靠使用者提示（`--gender`）；T1 交給 VLM
- [ ] 豐腴體型會被低估（覆蓋損失保守，避免被寬鬆衣服誤導）
- [ ] 卡通非 T-pose、卡通臉型（MediaPipe 在卡通臉上不可靠）
- [ ] 移植到 Web（JS 版 Anny 線性模型 + 擬合）

### Phase 3b — 頭髮、眉毛、睫毛、鞋子、眼鏡（不需 AI）✅

> 見 [[MakeHuman Proxies]]。全部 CC0 或程式生成，免下載大模型。

- [x] MakeHuman 系統素材包（CC0，約 280 MB，`template/build.sh` 會下載）：頭髮 10 款、眉毛 12、睫毛 4、鞋子 6
- [x] `.mhclo` 綁在 hm08（= Anny `anny-full`）→ 自動跟隨擬合體型，**繼承 52 個表情**（睫毛會眨、眉毛會動），繼承蒙皮權重
- [x] 髮型自動判斷（`fit/hair.py`）：MediaPipe 頭髮類別 → 垂到下巴下多少、臉側寬度、頭頂蓬度 → 長直髮 / 鮑伯 / 短髮 / 平頭 / 爆炸頭 / 無；綁起來（馬尾）正面看不出來 → 性別提示打破平手，使用者可覆寫
- [x] 髮色 / 眉色取樣並重新上色貼圖；alpha cutoff（glTF MASK）
- [x] **頭髮 spring bone**：垂到耳朵以下的頭髮依方位（後 / 左 / 右）自動生成 4 節骨鏈 + 頭 / 頸 / 胸 / 肩碰撞球；VRM1 `VRMC_springBone`、VRM0 `secondaryAnimation`；實測跑步時馬尾甩動
- [x] 鞋子（`fit/shoes.py`）：腳部分割為皮膚 → 光腳；否則依 HSV 選款並往照片鞋色調色；`delete_verts` 隱藏鞋內腳部面
- [x] 眼鏡（`fit/glasses.py`）：依 MediaPipe 眼角 / 眼瞼 / 鼻樑 / 臉側點程式生成鏡框（圓 / 方），綁頭骨；需手動開啟（無可靠自動偵測）
- [x] 貼圖修正：後腦填髮色僅限耳上頭皮（修正脖子咖啡色）；輪廓邊緣內縮 + 斜視角捨棄（修正白邊）；手只取皮膚像素、否則填膚色；軀幹背面不帶入照片中的手
- [x] 介面：生成頁籤只留「選擇照片」，性別 / 髮型 / 鞋子 / 眼鏡 / AI 背面收進「進階設定」
- [ ] 眼鏡自動偵測、帽子（目前戴帽會判成無髮）、服裝層（寬鬆衣物）
- [ ] 材質改 MToon（照片貼圖已含光影；PBR 在部分 app 顯得偏暗）

### Phase 3c — AI 三視圖（選用）✅

`--ai-turnaround` / 進階設定勾選。見 [[AI Turnaround]]。
- [x] FLUX.2-klein-4B（Apache-2.0）經 mflux 在 Apple Silicon（MLX / Metal）執行：下載約 4 分鐘、生成約 42 秒（4 步）、MLX 峰值 23 GB
- [x] 一張 1536×1024 三視圖（正 / 側 / 背，去眼鏡飾品、T-pose、白底）→ 分割三個人形 → 共用尺度正規化；側面朝向由鼻子 vs 耳朵判斷
- [x] 三視角共同擬合：共用體型 + 身體姿勢 + 相機尺度，每視角各自位移與**手臂微調**（AI 三視圖的手臂姿勢常不一致）；輪廓覆蓋留 1.5% 身高的衣物容許（避免被西裝撐胖）
- [x] 三視角貼圖：每 texel 取最正對且未被遮擋的視角；軀幹 / 腿不取皮膚像素（垂下的手）
- [x] 髮型從背面 / 側面判斷：垂過脖子 → 馬尾 / 長髮；側面後腦凸出 → **髮髻**（新增 CC0 hair01 素材包）
- [x] `--reuse-ai` 重用已生成的三視圖（調整選項不必重跑 AI）
- [ ] AI 生成的臉與本人相似度（目前臉部貼圖取自 AI 正面、臉型取自原照片）
- [ ] 三視圖不是 T-pose 時（常給 A-pose）已由姿勢擬合吸收；極端不一致時可能失敗 → 自動退回單張流程

### Phase 2b — Web 臉型擬合（移植）
- [ ] 一次性標註 MediaPipe 478 點 ↔ ICT 頂點對應（ICT 只附 68 點索引）
- [ ] JS Levenberg-Marquardt：ICT identity + 頭部姿態，加 PCA 先驗做正則化；用 facial transformation matrix 當初始值
- [ ] [[GLB Patching]]：改寫 POSITION / NORMAL / min-max，morph delta 保持不動，VRM 擴充欄位逐 byte 保留
- [ ] 用同一個人的多張照片評估穩定度

### Phase 3 — 貼圖 ✅ 幾何投影版（+ 選用 AI 背面）

`fit/texture.py`：每個 UV texel 反推到「照片姿勢」的網格 → 投影回照片取色。
- [x] 看得到 → 照片顏色；頭部用 478 點做 2D affine 對齊
- [x] 背向、但視線落在同一個身體部位（軀幹背面 → 軀幹正面）→ 正面顏色延伸到背面
- [x] 後腦 → 髮色（MediaPipe hair 類別中位數），沒有頭髮就用膚色
- [x] 其他（被別的部位擋住、輪廓外）→ UV 空間 Telea inpaint
- [x] 虹膜顏色取自 MediaPipe iris 點；鞏膜改偏灰、虹膜放大（之前看起來像瞪眼）
- [x] **選用 AI 背面**：`--ai-backview` / 生成頁籤勾選 → mflux + FLUX.2-klein-4B（Apache-2.0，未 gated）生成背面 → 背向 texel 優先採用；首次會安裝 `.venv-mflux` 並下載約 15 GB。失敗會自動退回幾何版
- [x] 回歸：9 張全部產出帶貼圖的 VRM；glTF validator 0 錯誤
- [ ] AI 背面尚未實測（等使用者決定是否下載 15 GB）
- 已知限制：背面會看到正面的圖案（領口、口袋）；大動作（坐 / 蹲）時被遮住的部位貼圖會糊；手臂貼在身體前面時會帶到衣服顏色；寬鬆長袍無法表現；照片臉很小時臉部貼圖解析度低
- [ ] 臉：照片投影到 ICT UV（在 WebGPU 上 render-to-texture），左右對稱補齊，LaMa ONNX 補洞（Apache，208 MB，放在 Worker 裡跑）
- [ ] 身體：用 MediaPipe 分割結果取膚色、衣服顏色；衣服先做成貼在身體上的貼圖
- [ ] 頭髮 → 見 Phase 5

### Phase 4 — Web 身材擬合
- [ ] 把 Anny 線性模型移植成 JS（blendshape + LBS）
- [ ] Pose world landmarks + 輪廓 → 身高、胖瘦、比例參數（只有一張照片，精度偏粗）

### Phase 5 — 頭髮與衣服（誠實說：這是最大的品質缺口）
- [ ] 零件庫：CC0 髮型 / 服裝 proxy（MPFB 授權待查），頭髮預先掛好 spring bone
- [ ] 選零件：分割結果 + 顏色 → 規則式；T1 用 [[oMLX]] 的 VLM 判斷
- [ ] T1：[[mflux]]（Qwen-Image-Edit-2511 / FLUX.2-klein-4B，Apache）生成背面視角 → 補齊背面貼圖

### Phase 6 — 桌面版與 CUDA
- [ ] Tauri v2 包 Web UI + Python sidecar（T1 模型第一次執行時才下載）
- [ ] T2：PSHuman / LHM 衣服幾何 → 包覆到範本外面當衣服層（研究題）
- [ ] Win / Linux 建置；MLX-CUDA 或 PyTorch CUDA 路徑

## 授權：預設全線可商用
Anny（Apache + CC0）· ICT-FaceKit（MIT）· MediaPipe（Apache）· Depth Anything V2 **Small**（Apache）· LaMa（Apache）· BiRefNet（MIT）· Qwen-Image-Edit-2511 / FLUX.2-klein-4B / Z-Image-Turbo（Apache）· VRM Add-on（MIT）。
**避開**：SMPL-X、RMBG、Sapiens、DSINE、MI-GAN、FLUX Kontext-dev / klein-9B、DA-V2 Base 以上。見 [[Licensing Matrix]]。

## 已知限制
- 貼在身體上的衣服看不出寬鬆衣物的外型；頭髮只能從零件庫挑 → 要靠 T1/T2 或更大的零件庫補
- 只有一張照片，深度資訊不足 → 側臉輪廓不準（MediaPipe 的 z 值很弱）
- Firefox Linux / Android 的 WebGPU 還沒正式上線 → 保留 WASM fallback；MediaPipe 官方只支援 Chrome / Safari

## 待決定
1. ~~Phase 0 spike：Anny 自帶的臉還是 ICT 頭？~~ → **Anny**（見 Phase 0b）
2. 頭髮 / 服裝零件庫的來源與授權
3. Web app 放哪：Cloudflare Pages（純前端，模型從 CDN 下載）？
