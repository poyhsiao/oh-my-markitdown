# Whisper 轉錄方案調查索引

> **Date:** 2026-04-05  
> **Author:** Kimhsiao

---

## 文件列表

本目錄包含以下 Whisper 轉錄方案的調查文件：

| 文件 | 說明 |
|------|------|
| [insanely-fast-whisper-evaluation.md](./insanely-fast-whisper-evaluation.md) | insanely-fast-whisper 取代評估報告（結論：不建議） |
| [whisper-alternatives-comparison.md](./whisper-alternatives-comparison.md) | 所有 Whisper 替代方案的完整比較矩陣 |
| [whisper-upgrade-plans.md](./whisper-upgrade-plans.md) | 四種推薦升級方案的深度分析與實施指南 |
| [whisper-performance-optimization.md](./whisper-performance-optimization.md) | 當前 faster-whisper 效能優化完整指南（6 種方案） |

---

## 快速結論

**不建議以 insanely-fast-whisper 取代目前的 faster-whisper。**

若追求效能提升，推薦優先考慮：

1. **方案 B（distil-whisper）** — 零程式碼改動，6 倍加速（僅英文）
2. **方案 A（BatchedInferencePipeline）** — 2-4 倍加速，多語言支援
3. **方案 C（whisperX）** — 說話者分離 + 精準字級時間戳

詳細分析請參閱上述文件。
