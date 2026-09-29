---
type: concept
verified: 2026-09-29
tags:
  - concept
  - web
  - vrm
  - export
---
在瀏覽器裡寫 VRM 的做法。

**為什麼不用現成工具**
- `@gltf-transform/core` 4.5.1：**沒註冊的擴充會被丟掉**；通用 pass-through 還是 issue #1856（v5 milestone），而且保不住對 bufferView / texture 的參照
- [[three-vrm]] 沒有 exporter（維護者在 discussion #1114 說 GLTFExporter plugin 因為 MToon 做不到可用）
- npm 上沒有維護中的 VRM exporter

**做法：直接 patch GLB binary**（估計幾百行 TS）
1. 解析 JSON chunk
2. 覆寫 base mesh 的 POSITION / NORMAL accessor bytes（頂點數相同，不用重建索引），更新 `min/max`
3. morph delta 視需要覆寫
4. 改寫骨頭 node translation、`inverseBindMatrices`
5. 替換圖片 bufferView → 重新排 BIN、修正 offset
6. `VRMC_vrm` / `VRMC_springBone` / VRM0 擴充**逐 byte 保留**
7. 用 [[vrm-validator]] 驗證

參考：WonderlandEngine viverse-example、zoan37/ChatVRM `optimize-vrm.mjs`（用自訂 Extension 保存原始 JSON 的做法）。
