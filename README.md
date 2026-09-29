# Single-Photo-VRM

**一張照片 → 可直接用的 VRM 虛擬人。** 拖進任何人形照片（T-pose 或任意姿勢、真人或卡通），自動產出：

- 標準 **humanoid 骨架**（含 30 根手指骨），可直接套用 Mixamo / VRMA 動作
- **Perfect Sync 臉部表情**：ARKit 52 個 blendshape（含嘴形、舌頭、眼球），iPhone Face ID 追蹤（iFacialMocap / Waidayo）→ VSeeFace / Warudo 一對一驅動
- 照片貼圖、頭髮（會隨動作飄動）、眉毛、睫毛、鞋子，選配眼鏡
- **VRM 0.x + VRM 1.0** 兩個版本（VSeeFace 用 0.x）

全部在 **Mac 本機**執行，不需要 CUDA；AI 三視圖為選配，用 Apple Silicon GPU（MLX）加速。

---

## 案例：插腰的西裝照

輸入只有一張正面照，手插在腰上、不是 T-pose：

<img src="docs/images/case_input.jpg" width="260" alt="輸入照片：插腰的西裝男子">

### 無 AI（預設，約 45 秒）

| 正面 | 背面 |
|---|---|
| ![無 AI 正面](docs/images/case_noai_front.jpg) | ![無 AI 背面](docs/images/case_noai_back.jpg) |

- 體型、臉型、姿勢都從這一張照片擬合；輸出一律是 T-pose
- 背面沒有照片可用 → 用正面顏色延伸到背面，所以背面也是西裝，但細節較少
- **限制**：插腰的手在正面照裡擋住了西裝，腰部會留下手的痕跡

### 有 AI 三視圖（勾選「AI 三視圖」，約 2 分鐘）

AI（FLUX.2-klein-4B）先把照片變成遊戲設計用的三視圖：正面、側面、背面，並去除眼鏡與臉部飾品：

![AI 三視圖](docs/images/case_turnaround.jpg)

| 正面 | 背面 |
|---|---|
| ![有 AI 正面](docs/images/case_ai_front.jpg) | ![有 AI 背面](docs/images/case_ai_back.jpg) |

- 三個視角**一起**擬合體型：側面決定胸、腹、臀的厚度
- 貼圖從最正對的視角取色 → **正面沒有手的痕跡、背面是真正的西裝背面**
- 臉部貼圖預設仍取自原始照片（較像本人），可改成 AI 正面（去除眼鏡）

---

## 快速開始

需求：Apple Silicon Mac、[Blender 5.x](https://www.blender.org/)（放在 `/Applications`）、[uv](https://github.com/astral-sh/uv)、Node.js 20+。

```bash
# 1. 一次性安裝：Python 環境、VRM Add-on、MediaPipe 模型、MakeHuman CC0 素材
template/build.sh

# 2. 啟動本機 API 與測試台
template/.venv/bin/python template/server.py   # http://127.0.0.1:5189
cd viewer && npm install && npm run dev         # http://localhost:5188
```

打開 <http://localhost:5188>，到 **生成** 頁籤拖入照片，完成後模型會自動載入，並提供 VRM 0.x / 1.0 下載。

也可以直接用指令：

```bash
template/.venv/bin/python template/photo2vrm.py photo.jpg                 # → build/out/photo.vrm0.vrm / .vrm1.vrm
template/.venv/bin/python template/photo2vrm.py photo.jpg --ai-turnaround # 加上 AI 三視圖
```

> 修改 `template/server.py` 或 pipeline 程式後，請重新啟動 `server.py`。

## 進階設定

測試台「生成 → 進階設定」與 CLI 參數對應：

| 設定 | CLI | 說明 |
|---|---|---|
| 性別 | `--gender female\|male` | 單張輪廓無法可靠判斷性別，預設自動（中性） |
| 髮型 | `--hair auto\|none\|<款式>` | 自動依照片判斷；綁起來的頭髮（馬尾、髮髻）正面看不到，可手動指定，或用 AI 三視圖從背面 / 側面判斷 |
| 鞋子 | `--shoes auto\|none\|shoes01–06` | 自動：腳部是皮膚 → 光腳，否則依顏色選款並調色 |
| 眼鏡 | `--glasses off\|round\|square` | 依臉部特徵點生成鏡框；目前需手動開啟 |
| AI 三視圖 | `--ai-turnaround` | 選配。首次下載約 15 GB，之後每張約 +1 分鐘 |
| 臉部貼圖 | `--face-texture photo\|ai` | AI 三視圖時，臉用原始照片（較像本人）或 AI 正面（去除眼鏡） |
| — | `--reuse-ai` | 沿用已生成的三視圖，調整其他選項時免重跑 AI |

## VRM Test Bench

`viewer/` 是瀏覽器測試台，任何 VRM 都能拖進來測試：

- **WASD** 移動、**Shift** 跑、**空白鍵** 跳，鏡頭跟隨；內建走 / 跑 / 跳動作，不需動畫檔
- 拖入 `.vrma` 或 Mixamo `.fbx` 播放，或指定為待機 / 走 / 跑 / 跳
- 表情滑桿、Perfect Sync 52 滑桿；**Webcam 即時驅動**（MediaPipe，全部在瀏覽器內處理）
- 相容性檢查：必要骨、手指、表情 preset、52 個 ARKit 分別對 VSeeFace（VRM0 PascalCase）與 Warudo（lowerCamel morph）檢查、lookAt、spring bone

## 運作方式

```
照片
 ├─ 去背、置中、MediaPipe 偵測（21 個身體點、478 個臉部點、51 個表情值）
 ├─ [選配] FLUX.2-klein-4B 三視圖 → 切成正 / 側 / 背三張
 ├─ 身體擬合：Anny 參數化人體（體型 + 姿勢 + 相機）對齊關鍵點與輪廓
 │     卡通比例（臉寬 / 身高 > 0.15）自動改用骨頭縮放的風格化模式
 ├─ 臉型擬合：478 點 → Anny 臉部參數（照片表情先扣除）
 ├─ 貼圖：每個 UV 點投影回照片（或三視圖）取色，被遮擋處補齊
 ├─ 頭髮 / 眉毛 / 睫毛 / 鞋子：MakeHuman CC0 素材自動套在擬合後的身體上
 └─ Blender（headless）：T-pose、humanoid 骨架、52 ARKit 表情、MToon 材質、
       頭髮 spring bone → VRM 1.0 + VRM 0.x
```

關鍵設計：身體與臉都用 **[Anny](https://github.com/naver/anny)**（NAVER，Apache-2.0 + CC0 素材）。它的 52 個臉部表情剛好就是 ARKit 52，網格內含舌頭、眼球與牙齒，所以不需要另外接頭或重做表情。

## 相容性

| 用途 | 檔案 |
|---|---|
| VSeeFace、VMagicMirror | `*.vrm0.vrm`（VRM 0.x，52 個 PascalCase clip） |
| Warudo、VNyan、three-vrm、VRoid Hub | `*.vrm1.vrm` 或 `*.vrm0.vrm` |
| iPhone 臉部追蹤 | iFacialMocap / Waidayo → 上述 app 的 Perfect Sync |

## 效能（M4 Max）

| 步驟 | 時間 |
|---|---|
| 去背 + 偵測 | 約 3 秒 |
| 身體 + 臉型擬合 | 約 15 秒 |
| 貼圖 + 頭髮 / 鞋子 | 約 10 秒 |
| Blender 產生 VRM | 約 10 秒 |
| **合計（無 AI）** | **約 40–60 秒** |
| AI 三視圖（選配） | +約 45 秒生成 + 三視角擬合；MLX 記憶體峰值約 23 GB |

## 授權與素材

| 元件 | 授權 |
|---|---|
| Anny 程式碼 / 素材 | Apache-2.0 / CC0 |
| MakeHuman 頭髮、眉毛、睫毛、鞋子（system assets、hair01） | CC0 |
| MediaPipe | Apache-2.0 |
| VRM Add-on for Blender | MIT / GPL-3.0 |
| FLUX.2-klein-4B（選配） | Apache-2.0 |
| three-vrm | MIT |

預設流程全部可商用。產出的 VRM 內含照片貼圖，請確認你有權使用輸入照片（例如圖庫照片的授權）。

## 已知限制

- 身體是貼身的 Anny 網格，寬鬆衣物（長袍、裙子）只能畫在身上，看不出外型
- 正面照看不到後腦：綁起來的頭髮請手動選或用 AI 三視圖
- 坐、蹲等大動作時被遮住的部位，貼圖會較模糊
- 卡通角色只支援 T-pose，而且不擬合臉型（MediaPipe 在卡通臉上不可靠）
- 眼鏡、帽子尚無自動偵測
- AI 三視圖的臉不一定像本人（因此臉部貼圖預設用原始照片）

## 專案結構

```
template/   Python pipeline：photo2vrm.py、server.py、fit/（去背、擬合、貼圖、頭髮、鞋子、三視圖）、Blender 建置腳本
viewer/     VRM Test Bench（Vite + three.js + three-vrm）
kb/         Obsidian 知識庫：調研、實作規劃、每個工具與坑的筆記（從 kb/00-MOC/Home.md 開始）
docs/       README 用圖
```

開發規劃與完整調研見 [`kb/00-MOC/Implementation Plan.md`](kb/00-MOC/Implementation%20Plan.md)。
