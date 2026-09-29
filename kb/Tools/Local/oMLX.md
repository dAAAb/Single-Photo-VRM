---
type: tool
stage: enhance
url: https://github.com/jundot/omlx
stars: 22400
license_code: "Apache-2.0"
license_weights: "—"
commercial: "✓"
last_update: 2026-09-24 v0.7.0rc1
verified: 2026-09-29
tags:
  - tool
  - local
  - mlx
  - mac
  - vlm
---
MLX 推論伺服器（從 vllm-mlx fork 出來），有 macOS 選單列 app 和 Homebrew service，提供 OpenAI / Anthropic 相容 API（`localhost:8000`），支援 paged SSD KV cache、continuous batching。

- **只跑 LLM / VLM / OCR / embedding / reranker，不能跑擴散模型或 3D 模型**
- 需 macOS 15+、Apple Silicon
- 用途：VLM 判斷照片屬性（髮型、服裝）→ 從零件庫挑選；VLM-as-judge 品質評分
