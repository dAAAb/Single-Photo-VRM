---
type: concept
verified: 2026-09-29
tags:
  - concept
  - perfect-sync
  - arkit
  - requirement
---
> [!important] 專案硬需求
> iPhone Face ID / TrueDepth 追蹤（iFacialMocap、Waidayo、Rokoko、Live Link Face）→ VSeeFace / Warudo / VNyan / three-vrm，**ARKit 52 blendshapes 一對一驅動**，含嘴形、`tongueOut`、`eyeLook*`。超越 Mixamo 只綁肢體。

## 各 app 偵測方式
| App | VRM | 方式 |
|---|---|---|
| [VSeeFace](https://www.vseeface.icu/) | **僅 VRM0**（VRM1 → `NotVrm0Exception`）| 52 個 BlendShapeClip **全部要存在**（空的也要）|
| [VMagicMirror](https://malaybaku.github.io/VMagicMirror/en/tips/perfect_sync/) | VRM0 | Clip 名 **PascalCase、大小寫敏感** |
| [Warudo](https://github.com/HakuyaLabs/warudo-docs) | VRM0 + 1 | 讀 **mesh morph 名**，**lowerCamel**，大小寫敏感；眼睛可用骨或 shape |
| VNyan | 支援（VRM1 未確認）| |
| [[three-vrm]] | VRM0/1 | VRM1 用 52 custom expression（社群慣例 lowerCamel）|

## 本專案匯出命名規則
1. mesh morph target = **lowerCamel ARKit**（`eyeBlinkLeft`）→ Warudo
2. VRM0 BlendShapeClip = **PascalCase**（`EyeBlinkLeft`）→ VSeeFace / VMM
3. VRM1 另出一版，custom expression lowerCamel
4. 另建 VRM preset（aa/ih/ou/ee/oh、blink、happy…）由 ARKit 組合而成，例如 blink = eyeBlinkLeft+Right、aa ≈ jawOpen

參考檔：[[hinzka 52blendshapes]]。

## 幾何需求
| 表情 | 需要 |
|---|---|
| `eyeLook*` | 獨立眼球，或眼骨 + VRM lookAt |
| `eyeBlink*` / `eyeSquint*` | 真實眼瞼 |
| `jawOpen`、`mouthFunnel`、`tongueOut` | 口腔、牙齒、牙齦、舌頭 |

> [!warning] 單圖重建模型都做不到
> [[PSHuman]] / [[SiTH]] / [[TRELLIS.2]] 是單一封閉表面，[[LHM]] 是 Gaussian → **臉部必須換成範本頭**（[[ICT-FaceKit]]），見 [[Head-Body Stitching]]。

## 傳輸協定
- **iFacialMocap**：UDP 49983，文字格式如 `mouthSmile_R-0|…=head#…|rightEye#…`，值 0–100、`_L/_R` 後綴需轉名（[開發者文件](https://www.ifacialmocap.com/for-developer/)）
- **VMC**：`/VMC/Ext/Blend/Val (string, float)` + `/VMC/Ext/Blend/Apply`，大小寫敏感（[spec](https://protocol.vmc.info/english.html)）
