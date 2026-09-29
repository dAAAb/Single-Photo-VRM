---
type: tool
stage: face
license_code: "見內文"
license_weights: "—"
commercial: "—"
last_update: 2026-09-29
verified: 2026-09-29
tags:
  - tool
  - face
  - fitting
---
單張照片 → 擬合頭部 + 貼圖。

  | 方法 | 授權 | 備註 |
  |---|---|---|
  | DECA / EMOCA / MICA | MPI 非商用 | FLAME |
  | [SMIRK](https://github.com/georgeretsi/smirk) | MIT，但依賴舊 FLAME | |
  | Pixel3DMM / [SHeaP](https://github.com/nlml/sheap) | CC-BY-NC | |
  | [TEASER](https://github.com/julia-cherry/Teaser_official) | 無 LICENSE | ICLR'25 |
  | [flame-head-tracker](https://github.com/PeizhiYan/flame-head-tracker) | MIT 包裝 | albedo 來自 BFM（非商用） |
  | [Deep3DFaceRecon](https://github.com/sicxu/Deep3DFaceRecon_pytorch) | MIT，用 BFM | |
  | [FFHQ-UV](https://github.com/csbhr/FFHQ-UV) | MIT | HiFi3D++ 拓樸、可轉 FLAME |
  | [FreeUV](https://github.com/YangXingchao/FreeUV) | CC-BY-NC-SA | CVPR'25 |

  > [!important] 結論
  > **沒有商用乾淨的 regressor。** 本專案做法：MediaPipe Face Landmarker（Apache-2.0）+ 自寫 landmark / photometric 優化，擬合 [[ICT-FaceKit]] 的 100 個 PCA identity → 照片投影到 ICT UV → inpaint 補遮擋 → 去光照。可在 Mac 跑。
