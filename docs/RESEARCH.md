# 單張照片 → VRM：現況調研（2026-09-29）

> 所有數據（stars、授權、日期）皆以一手來源查證：GitHub API / README / 原始碼、arXiv、HF model card、官網。
> 起點：Grok 的建議（LHM + Mesh2Motion + UniVRM）。以下先列查證結果，再列 Grok 漏掉的東西。

## TL;DR

1. **2026 年沒有任何開源工具能「一張照片 → 合格 VRM（含表情 + spring bone）」一步到位。** 每個研究模型都停在 3DGS 或 mesh。
2. **寫實路線的真正捷徑是 SMPL-X 權重直轉，不是再跑一次自動綁骨。** 重建模型本來就對齊 SMPL-X，骨架 1:1 對應 VRM humanoid（含手指），確定性、免 GPU。
3. **VRM 匯出可以完全無 Unity**：`pip install bpy-vrm-format`（VRM Add-on for Blender v4.9.1，2026-09-28）純 Python 匯出 VRM 1.0 / 0.x。
4. **授權是最大地雷**：SMPL-X 模型非商用；LHM++ 權重 CC BY-NC；多數 repo 無 LICENSE。目前整條寫實線只能算研究 / 個人用途。
5. **所有重建模型都需要 CUDA**，M4 Max 只能跑匯出 / 驗證端。

## Grok 說法查證

| Grok 說法 | 判定 | 備註 |
|---|---|---|
| LHM：ICCV'25、~2.7k★、Apache-2.0、`inference_mesh.sh` 可導 mesh | **部分錯** | 2,678★、Apache 屬實；但 `inference_mesh.sh` → `infer_mesh()` 實際呼叫 `save_ply()`，輸出是 **SMPL-X zero-pose 的 Gaussian .ply，不是三角網格** |
| LHM++ 2026 開源、0.79 s、輸出 3DGS .ply | 屬實 | 2026-03 釋出，693★，8 GB VRAM。**權重 `LICENSE_WEIGHT` = CC BY-NC 4.0**；預設 PixelShuffle 權重仍「pending」 |
| IDOL CVPR'25、SMPL-X UV Gaussian、HuGe100K | 屬實 | 328★；README 寫 MIT 但 repo 無 LICENSE 檔；HuGe100K 含 DeepFashion 非商用條款 |
| HumanLift SIGGRAPH Asia'25 | 屬實 | 24★，需 Wan2.1-14B + 手動 Photoshop 對齊步驟，不實用 |
| GeneMAN NeurIPS'25 | 屬實 | 98★、無授權、≥20 GB、優化式（慢）、未綁骨 |
| DiGS-Avatar（2026） | 屬實 | arXiv 2608.20759，6★，預訓練權重未明確釋出 |
| PERSONA（2026） | **年份錯** | 實為 ICCV 2025（arXiv 2508.09973），逐人優化，慢 |
| UniRig SIGGRAPH'25、HF 權重、ComfyUI-UniRig、MIA 人型路徑 | 大致屬實 | 1,779★ MIT；但釋出的權重是 Articulation-XL2.0，**VRoid/Rig-XL checkpoint 仍 pending**；骨架是通用的、**非 humanoid 命名**，不能直接對 VRM。MIA 路徑在 ComfyUI 節點（**GPL-3.0**）裡，不在 UniRig 本身 |
| Mesh2Motion ~3.3k★ MIT、v13 剛出、可離線 | 屬實（細節差） | 3,298★；Update 13 = 2026-09-25；離線是 Update 12 的獨立 desktop app。**純 GUI、手動擺骨，無 headless** → 不適合自動化 pipeline |
| AccuRIG 免費非開源 | 屬實 | GUI only，匯出需 ActorCore 帳號 |
| HY-Motion 1.0（2025-12、1B DiT） | 屬實 | 2025-12-30，1.0B + 0.46B Lite，arXiv 2512.23464；輸出 SMPL(-H) 系骨架，需 retarget；授權待查 `License.txt` |
| Kirakun0328/text-to-vrma | 屬實 | MIT，~183★ |
| MotionMind | 存在但玩具級 | 4 commits / 4★ |

**Grok 的結構性問題**：建議 LHM →（抽 mesh）→ Mesh2Motion/UniRig 重新綁骨，等於把重建模型已經附帶的 SMPL-X 骨架和 LBS 權重丟掉再猜一次。

## Grok 漏掉的重要項目

| 項目 | 為何重要 |
|---|---|
| [PSHuman](https://github.com/pengHTYX/PSHuman)（462★ MIT） | **輸出有貼圖 mesh，且與其擬合的 SMPL-X 對齊** → 權重轉移最省事。需 >40 GB VRAM、~1 min；最後更新 2024-12 |
| [SyncHuman](https://github.com/IGL-HKUST/SyncHuman)（NeurIPS'25, 82★, 無授權） | TRELLIS 系，輸出有貼圖 .glb；未對齊 SMPL-X |
| [SiTH](https://github.com/SiTH-Diffusion/SiTH)（219★ MIT） | 有貼圖 mesh + 擬合的 SMPL-X .obj |
| [ECON](https://github.com/YuliangXiu/ECON)（1.2k★，MPI 非商用） | 經典 SMPL-X 對齊 mesh + skinning transfer（avatarizer）範例程式 |
| [Make-It-Animatable (MIA)](https://github.com/jasongzy/Make-It-Animatable)（CVPR'25, 458★, MIT/Apache） | **輸出 Mixamo 65 骨命名（含手指）** → 直接對 VRM。<1 s。v2 分支改用 Hunyuan3D ShapeVAE（帶 Tencent 授權），建議用 v1 main |
| [AniGen](https://github.com/VAST-AI-Research/AniGen)（SIGGRAPH'26, 506★, 2026-09-28） | 單圖一次出 mesh + 骨架 + 權重；但骨架非 humanoid、無表情 |
| [StdGEN](https://github.com/hyz317/StdGEN)（CVPR'25, 394★ Apache） | 二次元單圖 → A-pose mesh，**身體 / 衣服 / 頭髮分層**（用 VRoid 資料訓練）→ 頭髮層可直接掛 spring bone |
| [CharacterGen](https://github.com/zjp-shadow/CharacterGen)（834★ Apache） | 二次元 A-pose mesh；作者自己也是用 Mixamo/AccuRig 綁骨 |
| [TRELLIS.2](https://github.com/microsoft/TRELLIS.2)（11.4k★ MIT） | 最強開源通用有貼圖 mesh；無綁骨 |
| [SAM 3D Body](https://github.com/facebookresearch/sam-3d-body)（3.6k★） | 人體姿態估計比 SMPLer-X 強；輸出 MHR 身體（非 SMPL-X） |

## VRM 匯出（無 Unity）

- **[VRM Add-on for Blender](https://github.com/saturday06/VRM-Addon-for-Blender)** v4.9.1（MIT/GPL-3.0），PyPI [`bpy-vrm-format`](https://pypi.org/project/bpy-vrm-format/) 可不裝 Blender。
  [Scripting API](https://vrm-addon-for-blender.info/en-us/scripting-api/)（名稱已對原始碼確認，**尚未實跑**）：
  - 骨架：`vrm1.humanoid.human_bones.<bone>.node.bone_name`；`bpy.ops.vrm.assign_vrm1_humanoid_human_bones_automatically`
  - 表情：`vrm.assign_vrm1_expressions_from_arkit`（ARKit 52 → VRM）、`vrm.assign_vrm1_expressions_automatically`
  - spring bone：`spring_bone1.{springs, colliders, collider_groups}`；meta / lookAt / firstPerson / MToon 皆可設
  - 匯出：`bpy.ops.export_scene.vrm`（1.0 預設，可選 0.x）、`bpy.ops.export_scene.vrma`
- UniVRM（Unity, v0.131.2）：batchmode 理論可行但無官方文件，且需 Unity 授權 → 不採用。
- three-vrm（v3.5.5）：**只能載入，不能匯出**。
- 找不到其他可維護的獨立 VRM writer。

### VRM 1.0 合格清單
1. `VRMC_vrm` 必要：`specVersion`、`meta`（`name`、`authors[]`、`licenseUrl`）、`humanoid`
2. 15 根必要骨：hips, spine, head, 左右 upperLeg/lowerLeg/foot, 左右 upperArm/lowerArm/hand
3. 骨架父子鏈依規格；正 scale；rest pose 為面向 +Z 的 T-pose
4. 實務上各 app 期待：表情 preset（aa/ih/ou/ee/oh、blink(L/R)、happy/angry/sad/relaxed/surprised、lookUp/Down/Left/Right）、lookAt、firstPerson、MToon 或 unlit、spring bone
5. **VSeeFace 只吃 VRM 0.x** → 兩版都要出
6. 驗證器：[mrxz/vrm-validator](https://github.com/mrxz/vrm-validator)（CLI）

### 表情
- ARKit 52 deformation transfer：[deformation_transfer_ARkit_blendshapes](https://github.com/vasiliskatr/deformation_transfer_ARkit_blendshapes)（MIT）+ [ICT-FaceKit](https://github.com/ICT-VGL/ICT-FaceKit)（MIT，52 ARKit 範本頭）→ `assign_vrm1_expressions_from_arkit`
- SMPL-X 的臉就是 FLAME 系拓樸，其 expression basis 可直接烘成 shape key（但語意非 ARKit，需手動組合 viseme）

### 動作（VRMA）
- BVH → VRMA：[vrm-c/bvh2vrma](https://github.com/vrm-c/bvh2vrma)（官方）
- Mixamo FBX → VRMA：[fbx2vrma-converter](https://github.com/tk256ailab/fbx2vrma-converter)
- 任意格式 → Blender retarget → `export_scene.vrma`（最可腳本化）
- 生成：[HY-Motion 1.0](https://github.com/Tencent-Hunyuan/HY-Motion-1.0)、[text-to-vrma](https://github.com/Kirakun0328/text-to-vrma)

## SMPL-X → VRM 骨架對應

| SMPL-X | VRM 1.0 |
|---|---|
| pelvis | hips |
| spine1 / spine2 / spine3 | spine / chest / upperChest |
| neck / head / jaw | neck / head / jaw |
| left_eye_smplhf / right_eye_smplhf | leftEye / rightEye |
| L/R collar | L/R shoulder |
| L/R shoulder / elbow / wrist | L/R upperArm / lowerArm / hand |
| L/R hip / knee / ankle / foot | L/R upperLeg / lowerLeg / foot / toes |
| thumb1-3 | ThumbMetacarpal / ThumbProximal / ThumbDistal |
| index/middle/ring/pinky 1-3 | Proximal / Intermediate / Distal |

找不到維護中的現成 smplx→VRM 轉換器；最接近的積木：[官方 SMPL-X Blender add-on](https://gitlab.tuebingen.mpg.de/jtesch/smplx_blender_addon)（Blender 4.5+）、[SMPL-to-FBX](https://github.com/softcat477/SMPL-to-FBX)（MIT，停更）。**這段要自己寫，但規模小。**

## 商用基準線

| 服務 | 照片輸入 | 出 VRM | 備註 |
|---|---|---|---|
| Ready Player Me | — | — | **2026-01-31 關站**（Netflix 收購） |
| VTubeMe | 自拍 | **是**（54 骨、66 表情 morph） | 寫實，基於 MetaPerson，$7.99/個，無 API → **品質對照組** |
| MetaPerson / Avatar SDK | REST API | GLB/FBX | $800/月 6,000 個 |
| Avaturn | API | GLB/FBX | $800/月 1,000 個 |
| Tripo / Meshy | API | 否（有 humanoid auto-rig API，Tripo 可 `spec=mixamo`） | 付費雲端 |
| VRoid Studio | 無 | 原生 | 無 API，`.vroid` 格式未公開 |

## 授權矩陣

| 元件 | 程式碼 | 權重 / 資料 | 商用 |
|---|---|---|---|
| SMPL-X model | — | 非商用（商用需找 Meshcapade）；單一匯出身體可用 CC-BY 的 SMPL-X Body license | ✗ |
| LHM | Apache | Apache | 受 SMPL-X 限制 |
| LHM++ | Apache | **CC BY-NC** | ✗ |
| PSHuman | MIT | HF | 受 SMPL-X 限制 |
| ECON | MPI 非商用 | — | ✗ |
| MIA v1 | MIT | Apache | ✓ |
| StdGEN / CharacterGen | Apache | Apache | ✓（查訓練資料條款） |
| VRM Add-on for Blender | MIT/GPL | — | ✓ |
| ComfyUI-UniRig | GPL-3.0 | — | 再散布注意 |
| RigAnything | Adobe 非商用 | — | ✗ |

## Perfect Sync（ARKit 52 臉部表情，Face ID Cam 相容）

> 需求：iPhone TrueDepth 追蹤（iFacialMocap / Waidayo / VMC）→ VSeeFace / Warudo / VNyan / three-vrm，52 個表情一對一驅動，含嘴形、舌頭、眼球。

### 各 app 怎麼認

| App | VRM 版本 | 偵測方式 |
|---|---|---|
| [VSeeFace](https://www.vseeface.icu/) | **僅 VRM0**（VRM1 拋 `NotVrm0Exception`） | 52 個 **BlendShapeClip 全部要存在**（空的也要） |
| [VMagicMirror](https://malaybaku.github.io/VMagicMirror/en/tips/perfect_sync/) | VRM0 | Clip 名 **PascalCase、大小寫敏感**：`EyeBlinkLeft`、`JawOpen`、`TongueOut` |
| [Warudo](https://github.com/HakuyaLabs/warudo-docs) | VRM0 + VRM1 | 讀 **mesh morph target 名稱**，**lowerCamel ARKit**（`eyeBlinkLeft`），大小寫敏感 |
| three-vrm | VRM0/1 | VRM1 用 52 個 custom expression（社群慣例 lowerCamel，未有官方標準） |

**最安全的匯出命名**：mesh morph = lowerCamel（Warudo）＋ VRM0 clip = PascalCase（VSeeFace/VMM）＋ 另出 VRM1（custom expression lowerCamel）。
參考檔：hinzka `VRoid_V110_Female_v1.1.3.vrm` = VRM preset + 52 個 PascalCase clip（已實際解析檔案確認）。

傳輸：iFacialMocap UDP 49983，值 0–100、`_L/_R` 後綴需轉名；VMC `/VMC/Ext/Blend/Val` + `/Apply`，大小寫敏感。

### 幾何需求 vs 重建模型輸出
- `eyeLook*` 需獨立眼球（或眼骨 + lookAt）；`eyeBlink/Squint` 需真實眼瞼；`jawOpen/mouthFunnel/tongueOut` 需口腔、牙齒、牙齦、舌頭。
- PSHuman / SiTH / TRELLIS.2 = 單一封閉表面；LHM = Gaussian。**都沒有眼球和口腔 → 臉部必須換成範本頭。**

### 範本頭

| 範本 | 眼 | 口腔 | ARKit | 授權 |
|---|---|---|---|---|
| **[ICT-FaceKit](https://github.com/ICT-VGL/ICT-FaceKit)** | 眼球、鞏膜、淚液、睫毛 | **口腔、牙齦+舌、32 顆牙** | 53 個 ARKit 命名 OBJ（`browInnerUp`/`cheekPuff` 分 L/R；**缺 `tongueOut`**）；100 個 PCA identity mode，無 albedo | **MIT** |
| FLAME 2023 Open | 眼球 + 眼關節 | 無 | 無 ARKit | CC-BY-4.0（2025-11；舊版非商用） |
| SMPL-X 頭部 | — | — | — | 已由官方 `SMPL-X__FLAME_vertex_ids.npy` 確認為 FLAME 拓樸 |
| MPFB faceunits01 | 未確認 | 未確認 | 54 個（含舌） | 素材包授權不明 |
| MetaHuman | 完整 | 完整 | ARKit 可對 | UE EULA：**禁止訓練 AI**、偏重 |

### 照片 → 擬合頭部

| 方法 | 授權 |
|---|---|
| DECA / EMOCA / MICA | MPI 非商用 |
| SMIRK | MIT，但依賴舊版 FLAME（非商用） |
| Pixel3DMM / SHeaP | CC-BY-NC |
| [flame-head-tracker](https://github.com/PeizhiYan/flame-head-tracker) | MIT 包裝 DECA/MICA，albedo 用 BFM（非商用） |
| [FFHQ-UV](https://github.com/csbhr/FFHQ-UV) | MIT（HiFi3D++ 拓樸） |
| FreeUV | CC-BY-NC-SA |

→ **沒有商用乾淨的 regressor。** 商用乾淨解：MediaPipe landmarks（Apache）+ 自寫優化擬合 ICT PCA identity（MIT），照片投影到 ICT UV 再 inpaint。

### 產生 52 shapes
- 保留 ICT 拓樸 → **不需要 shape transfer**，直接套 ICT 表情 delta 到擬合後的 identity；`tongueOut` 在範本上手雕一次。
- 任意頭 mesh 備案：[deformation_transfer_ARkit_blendshapes](https://github.com/vasiliskatr/deformation_transfer_ARkit_blendshapes)（MIT）、[NFR](https://github.com/dafei-qin/NFR_pytorch)（MIT）。
- 商用 GUI（Faceit、Polywink、HANA_Tool）不適合自動化。

### 頭身接合
無開源參考實作。建議：身體對齊 SMPL-X → 用 SMPL-X↔FLAME 對應定位 → 切掉重建頭部至頸環 → 2–3 cm 帶 RBF/Laplacian 混合 → 頸部用 SMPL-X 權重 → UV 空間 color transfer / Poisson 融膚色。

### 二次元
- [hinzka/52blendshapes-for-VRoid-face](https://github.com/hinzka/52blendshapes-for-VRoid-face)：README 允許商用、再散布、免標示（但檔內 VRM meta 寫 `Redistribution_Prohibited`，以 README 為準）。
- [blender-vrm-perfect-sync](https://github.com/elainyilanchen/blender-vrm-perfect-sync)（MIT，headless Blender）：VRoid 臉拓樸一致 → 逐頂點把 donor 的 52 shapes 拷到任意官方 VRoid 臉。
