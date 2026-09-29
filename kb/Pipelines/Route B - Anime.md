---
type: pipeline
status: planned
tags:
  - pipeline
  - anime
---
1. 照片 → VLM 屬性（髮型、髮色、瞳色、膚色、服裝）
2. [[Anime Template Assembly]]：從零件庫挑選 + 調色；臉貼圖風格化 img2img
3. [[hinzka 52blendshapes]] base + [[blender-vrm-perfect-sync]]
4. 進階：[[StdGEN]] 分層頭髮 / 衣服 → 綁到 base，頭髮加 spring bone
5. [[VRM Add-on for Blender]] 匯出 VRM0 + VRM1

全線可商用。退路（今天就能跑）：[[StdGEN]] / [[CharacterGen]] → [[Make-It-Animatable]] → VRM，但臉 / 頭髮需手動修。
