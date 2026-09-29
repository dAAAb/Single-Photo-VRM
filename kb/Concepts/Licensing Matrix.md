---
type: concept
verified: 2026-09-29
tags:
  - concept
  - license
  - decision
---
| 元件 | 程式碼 | 權重 / 資料 | 商用 |
|---|---|---|---|
| [[SMPL-X]] model | — | 非商用（Meshcapade 商授）| ✗ |
| [[LHM]] | Apache | Apache | 受 SMPL-X 限制 |
| [[LHM++]] | Apache | **CC BY-NC** | ✗ |
| [[PSHuman]] | MIT | HF | 受 SMPL-X 限制 |
| [[ECON]] | MPI 非商用 | — | ✗ |
| [[Make-It-Animatable]] v1 | MIT | Apache | ✓ |
| [[UniRig]] | MIT | MIT | ✓ |
| ComfyUI-UniRig | GPL-3.0 | — | 再散布注意 |
| RigAnything | Adobe 非商用 | — | ✗ |
| [[ICT-FaceKit]] | MIT | MIT | ✓ |
| [[FLAME]] 2023 Open | — | CC-BY-4.0 | ✓ |
| DECA / EMOCA / MICA / Pixel3DMM / FreeUV / BFM | — | 非商用 | ✗ |
| MediaPipe | Apache | Apache | ✓ |
| [[StdGEN]] / [[CharacterGen]] | Apache | Apache | ✓（查訓練資料）|
| [[hinzka 52blendshapes]] | README 允許 | — | ✓ |
| [[VRM Add-on for Blender]] | MIT/GPL | — | ✓ |
| [[TRELLIS.2]] | MIT | MIT | ✓ |
| [[Anny]] | Apache | CC0（SMPL-X 拓樸選項 ✗）| ✓ |
| [[Meta MHR]] / [[GNM Head]] | Apache | Apache | ✓ |
| [[MediaPipe Tasks Vision]] | Apache | CC-BY-4.0 | ✓ |
| Depth Anything V2 Small / LaMa / BiRefNet | Apache / Apache / MIT | 同 | ✓ |
| DA-V2 Base+ / RMBG / Sapiens / DSINE | — | 非商用 | ✗ |
| MI-GAN | MIT？ | 疑似衍生自 NC | ⚠️ |
| [[mflux]]：Qwen-Image-Edit-2511 / FLUX.2-klein-4B / Z-Image-Turbo | MIT | Apache | ✓ |
| FLUX.1 Kontext-dev / FLUX.2-klein-9B | — | BFL 非商用 | ✗ |
| Apple SHARP / LiTo | Apple | 研究用 / Apple 條款 | ✗ / ⚠️ |
| [[oMLX]] | Apache | — | ✓ |

## 組合
- **v2 預設（Web 優先）**：[[Template Morphing]] 整條可商用
- **研究 / 個人**：[[PSHuman]] + [[SMPL-X Weight Transfer]] + [[ICT-FaceKit]]
- **商用乾淨**：[[TRELLIS.2]] + [[Make-It-Animatable]] v1（或買 SMPL-X 商授）+ [[ICT-FaceKit]] + 自寫 MediaPipe 擬合（[[Photo to Face Fitting]]）
- **二次元**：全線可商用
