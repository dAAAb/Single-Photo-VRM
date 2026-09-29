---
type: tool
stage: preview
url: https://github.com/pixiv/three-vrm
stars: 2190
license_code: "MIT"
license_weights: "—"
commercial: "✓"
last_update: 2026-07-09
verified: 2026-09-29
tags:
  - tool
  - export
  - web
---
v3.5.5。**只能載入 / 渲染，不能匯出**。`@pixiv/three-vrm-animation` 播放 VRMA。

  預覽 harness：
  1. `GLTFLoader` 註冊 `VRMLoaderPlugin` + `VRMAnimationLoaderPlugin`
  2. `gltf.userData.vrm`、`gltf.userData.vrmAnimations[0]`
  3. `createVRMAnimationClip(vrma, vrm)` → `AnimationMixer`
  4. 每幀 `mixer.update(dt)` + `vrm.update(dt)`
  5. Playwright：截 T-pose、動作中、逐一 `expressionManager.setValue` 的畫面

  要走 http，不要 `file://`。[官方範例](https://pixiv.github.io/three-vrm/packages/three-vrm/examples/)
