---
type: concept
verified: 2026-09-29
tags:
  - concept
  - assets
  - cc0
---
# MakeHuman Proxies

來源：MakeHuman 官方「system assets」素材包（`makehuman_system_assets_cc0.zip`，約 280 MB，每項標 **CC0**）→ `third_party/makehuman_assets/system/`（不進 git，`template/build.sh` 下載）。

| 類別 | 項目 |
|---|---|
| hair | afro01, bob01, bob02, braid01, long01, ponytail01, short01–04 |
| eyebrows | eyebrow001–012 |
| eyelashes | eyelashes01–04 |
| clothes（鞋） | shoes01 棕皮鞋、02 休閒鞋、03 黑靴、04 黑皮鞋、05 白運動鞋、06 藍運動鞋 |
| 其他（未用） | skins（CC0 皮膚貼圖）、eyes 材質、衣服、fedora |

另有 hair01 素材包（217 MB，CC0，風格化髮型）可擴充。

## `.mhclo` 格式
- 每個 proxy 頂點：3 個 hm08 基礎頂點索引 + 3 個重心權重 + 3 個偏移；偏移乘上 `x/y/z_scale v1 v2 den` 的尺度（兩頂點距離 / den）
- `delete_verts` 自成一行，範圍寫在後續行，格式 `4793 - 4846`（減號前後有空格）
- `material` 行可能出現在 `verts` 之前 → 不能用它當作頂點區段結束
- 座標：**Anny = 0.1 × (x, −z, y)_MakeHuman**（在範本上驗證誤差 1e-8）
- 素材附的 `.obj` 多半是在 MakeHuman 預設體型上匯出 → 和原始基礎網格比會差 0.6–1 dm，不代表套用錯誤（渲染確認貼合）

## 在本專案的用法（`fit/proxies.py`）
- 位置：`fit(p, V_anny_full)`；表情：`delta(p, D)` = 參考頂點差值的重心混合 → 睫毛眨眼、眉毛上揚免費
- 權重：參考頂點蒙皮權重的重心混合（取前 N 個）
- 匯出：`export_anny.py --proxies proxies.json`，在壓縮前套上，之後附加到同一網格、各自材質（`face_group`）
