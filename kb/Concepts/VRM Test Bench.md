---
type: tool
stage: qa
verified: 2026-09-29
tags:
  - concept
  - qa
  - web
---
# VRM Test Bench

repo `viewer/`，用 Vite + three.js + [[three-vrm]] 做的瀏覽器測試台。**每個階段都用它驗收**，也能測任何現有的 VRM。

```bash
cd viewer && npm install && npm run dev   # http://localhost:5188
# 直接帶模型：http://localhost:5188/?model=./samples/xxx.vrm
```

## 功能
| 頁籤 | 內容 |
|---|---|
| 檢查 | VRM 版本、15 根必要骨、選配骨、30 根手指骨、VRM preset、[[Perfect Sync]] 52 個（分別檢查 VSeeFace 的 PascalCase clip 和 Warudo 的 lowerCamel mesh morph）、lookAt、spring bone、firstPerson、meta |
| 動作 | 待機 / 走 / 跑 / 跳 各自可指定載入的動作，預設用內建程序式動作；已載入動作的播放清單；視線跟隨、spring bone 開關、回到原點、截圖 |
| 表情 | VRM 表情滑桿 |
| Perfect Sync | 52 個 ARKit 滑桿，缺的標紅，圓點顏色表示相容 VSeeFace 還是 Warudo |
| Webcam | [[MediaPipe Tasks Vision]] 追蹤臉 → 即時驅動 52 表情 + 頭部轉動；鏡像開關；沒 Perfect Sync 的模型用 preset 近似 |

**操作**：WASD 移動（依鏡頭方向）· Shift 跑 · 空白鍵 跳 · 滑鼠拖曳轉鏡頭 · 滾輪縮放。拖放 `.vrm` / `.vrma` / Mixamo `.fbx`；檔名含 idle / walk / run / jump 的動作會自動指定到對應狀態。

## 實作重點
- 程序式動作直接驅動 normalized humanoid bone，當作**底層**；載入的動作只覆寫它有動到的骨頭（VRMA 只動部分骨頭時，其他骨頭不會卡在 T-pose）
- VRM0 的 normalized 空間面向 -Z（three-vrm 會把 scene 轉 180°）→ 程序式動作的 X / Z 旋轉要反號
- Mixamo FBX 的 retarget 改寫自 three-vrm humanoidAnimation 範例（MIT）；會移除水平方向的 root motion，因為角色移動改由控制器負責
- 表情只覆寫有被滑桿或 webcam 設定過的，**VRMA 裡的表情軌才能正常播放**
- `window.__bench.frame(dt)` 可以逐幀推進（背景分頁的 rAF 會暫停，自動化測試要用它）

## 已驗證（2026-09-29，Chrome）
- hinzka Perfect Sync VRM0：檢查頁 52/52（VSeeFace 和 Warudo 都通過）；jawOpen / tongueOut / eyeBlinkLeft / browInnerUp 有正確變形
- VRM1 sample + three-vrm 範例 `test.vrma`：骨頭、`happy` 表情、lookAt 軌都有播放
- 走 / 跑 / 跳的姿勢和鏡頭跟隨；VRM0 手臂方向正確
- MediaPipe FaceLandmarker 能用 GPU delegate 建立

## 尚未驗證
- **webcam 實際追蹤**：左右鏡像、頭部 pitch 方向需要真人測
- **Mixamo FBX**：還沒有測試檔
- Safari / Firefox
