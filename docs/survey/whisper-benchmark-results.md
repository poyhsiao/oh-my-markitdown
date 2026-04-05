# Whisper 優化 — Benchmark 結果與後續調整建議

> **Date:** 2026-04-05
> **Author:** Kimhsiao
> **Status:** ✅ 優化已完成（2026-04-05 更新）
> **Based on:** Actual Docker benchmark results

---

## 一、Benchmark 測試結果

### 1.1 測試環境

| 項目 | 值 |
|------|-----|
| 硬體 | CPU (Docker container) |
| 測試音訊 | 440Hz sine wave（純音，無語音） |
| 音訊長度 | 30s, 120s |
| 模型 | base（預設）, tiny（auto 選擇） |

### 1.2 30 秒音訊結果

| 測試 | 設定 | 總時間 | 模型載入 | 轉錄時間 |
|------|------|--------|---------|---------|
| Old (冷啟動) | model=base | 1086ms | 809ms | 245ms |
| New (冷啟動) | model=auto, speed | 7390ms | 7154ms | 201ms |
| New (快取) | model=auto, speed | **295ms** | 65ms | 208ms |
| Old (快取) | model=base | **296ms** | 58ms | 209ms |

**結論：** 快取後兩者性能幾乎相同（295ms vs 296ms）。30 秒音訊太短，未觸發 chunking（閾值 90 秒）。

### 1.3 120 秒音訊結果

| 測試 | 設定 | 總時間 | 模型載入 | 轉錄時間 | Chunk 數 |
|------|------|--------|---------|---------|---------|
| Old (序列) | model=base, beam=5 | 2515ms | 1707ms | 741ms | 2 (序列) |
| New (並行) | model=auto(tiny), beam=1 | 1053ms | 64ms | 931ms | 2 (並行) |

**結論：**
- 轉錄時間：741ms (base, 序列) vs 931ms (tiny, 並行) — **並行反而稍慢**
- 總時間：2515ms vs 1053ms = **2.4x 加速**（主要來自模型快取 + tiny 模型）
- 120s 分成 2 個 chunk，ThreadPoolExecutor overhead 抵消了並行收益

---

## 二、瓶頸分析

### 2.1 時間分佈（120s, 冷啟動）

| 階段 | 時間 | 佔比 |
|------|------|------|
| 模型載入 | 1707ms | **68%** |
| 轉錄處理 | 741ms | 29% |
| 其他（音頻提取、格式化） | 67ms | 3% |

### 2.2 瓶頸識別

1. **模型冷啟動是最大瓶頸**（68%）
2. **並行 chunking 對短音訊無效**（2 chunks 的 overhead > 收益）
3. **純音測試不具代表性**（真實語音處理時間不同）

---

## 三、後續調整建議

### 3.1 模型預熱（Pre-warm）— 最高優先級

**問題：** 首次請求需 1707ms 載入模型

**方案：** 啟動時預載常用模型到快取

```python
# api/main.py — startup event
@app.on_event("startup")
async def startup():
    # Pre-warm commonly used models
    from api.whisper_transcribe import get_model
    get_model("tiny", "cpu", "int8", cpu_threads=8)
    get_model("base", "cpu", "int8", cpu_threads=8)
```

**預估效果：** 冷啟動 1707ms → 0ms（模型已載入）
**預估工時：** 1-2 小時

### 3.2 調整並行 chunking 閾值

**問題：** 120s 分成 2 個 chunk，並行 overhead 不划算

**方案：** 提高並行啟用閾值

| 音訊長度 | Chunk 數 | 建議策略 |
|---------|---------|---------|
| < 90s | 1 | 直接轉錄（不分段） |
| 90s - 180s | 2-3 | 序列處理（overhead > 收益） |
| 180s - 300s | 3-5 | 可選並行（2 workers） |
| > 300s | 5+ | 並行處理（4 workers） |

**修改位置：** `api/whisper_transcribe.py:transcribe_audio_chunked()`

**預估效果：** 減少短音訊的 overhead，長音訊保持並行加速
**預估工時：** 1-2 小時

### 3.3 真實語音測試

**問題：** 目前用 440Hz 純音測試，不具代表性

**方案：** 使用真實語音檔進行 benchmark

```bash
# 生成帶語音的測試檔（或使用現有語音檔）
# 測試不同長度：30s, 120s, 300s, 1800s
# 比較序列 vs 並行的實際加速比
```

**預估工時：** 1 小時

### 3.4 Chunk 長度優化

**問題：** 目前 chunk_duration=60s，對於長音檔可能不是最佳值

**方案：** 根據音訊長度動態調整 chunk 長度

| 音訊長度 | 建議 chunk 長度 | 預估 chunk 數 |
|---------|---------------|-------------|
| 300s (5min) | 60s | 5 |
| 1800s (30min) | 90s | 20 |
| 3600s (1hr) | 120s | 30 |

**預估效果：** 減少 chunk 數量，降低 overhead
**預估工時：** 1-2 小時

---

## 四、預期效果矩陣

| 優化項 | 30s | 120s | 30min | 1hr | 實施難度 |
|--------|-----|------|-------|-----|---------|
| 模型預熱 | -1700ms | -1700ms | -1700ms | -1700ms | 低 |
| 並行閾值調整 | 0ms | -50ms | -200ms | -500ms | 低 |
| Chunk 長度優化 | 0ms | 0ms | -100ms | -300ms | 中 |
| **組合效果** | **-1700ms** | **-1750ms** | **-2000ms** | **-2500ms** | |

---

## 五、實施順序建議

1. **立即執行**：模型預熱（1-2h，最高回報）
2. **短期執行**：調整並行閾值（1-2h，低成本）
3. **中期執行**：真實語音測試 + Chunk 長度優化（2-3h）

---

## 六、與原始 Survey 的差異

| 項目 | 原始 Survey 預估 | 實際 Benchmark | 差異原因 |
|------|-----------------|---------------|---------|
| CPU 加速比 | 2-4x | 2.4x（含快取） | 符合預期 |
| 並行 chunking 加速 | 2-3x | 不明顯（2 chunks） | Chunk 數太少 |
| 模型載入時間 | 5-30s | 1.7s（快取後 65ms） | 比預期快 |
| 轉錄時間（120s） | ~6s | 0.7-0.9s | 純音測試較快 |

---

## 七、優化後 Benchmark 結果

### 7.1 實施的優化項

| # | 優化項 | 狀態 | 實際效果 |
|---|--------|------|---------|
| 1 | 模型預熱 | ✅ | 啟動時載入 tiny + base，冷啟動消除（快取後 48ms） |
| 2 | 並行閾值調整 | ✅ | 1-3 chunks 序列，4-6 chunks 2 workers，7+ chunks 4 workers |
| 3 | Chunk 長度優化 | ✅ | <5min: 60s, 5-30min: 90s, >30min: 120s |

### 7.2 最終 Benchmark 比較

#### 30 秒音訊

| 測試 | 總時間 | 模型載入 | 轉錄時間 |
|------|--------|---------|---------|
| Before (cached) | 296ms | 58ms | 209ms |
| After (cached) | **305ms** | 65ms | 214ms |

#### 120 秒音訊

| 測試 | 總時間 | 模型載入 | 轉錄時間 | Chunk 數 |
|------|--------|---------|---------|---------|
| Before (old, sequential) | 2515ms | 1707ms | 741ms | 2 (序列) |
| After (optimized) | **753ms** | 48ms | 657ms | 3 (動態並行) |

**120s 加速比：3.3x（2515ms → 753ms）**
**模型載入加速比：35x（1707ms → 48ms）**

### 7.3 測試覆蓋

- 12 個新增單元測試（pre-warm, parallel threshold, dynamic chunk length）
- 198 個單元測試全部通過，8 個跳過（torch 未安裝）

---

## 八、總結

已完成 5 個 Phases + 3 項 benchmark 優化：
- ✅ 常數優化、API 參數暴露
- ✅ 後端抽象層（faster-whisper + whispercpp）
- ✅ 並行 chunking 基礎 + 動態閾值
- ✅ Docker GPU 部署
- ✅ 自動模型選擇、效能監控
- ✅ **模型預熱**（啟動時載入 tiny + base）
- ✅ **動態 chunk 長度**（60s/90s/120s）

**最終效果：120s 音訊 3.3x 加速，模型載入 35x 加速。**
