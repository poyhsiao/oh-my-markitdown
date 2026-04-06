# Whisper 轉錄效能優化方案

> **Date:** 2026-04-05
> **Author:** Kimhsiao
> **Status:** 待評估實施

---

## 一、現況分析

### 1.1 目前轉錄流程

```
API Request
    │
    ├── Concurrency Manager（最多 3 個並行請求）
    │
    ├── YouTube 場景
    │   ├── Fast Path: YouTube 字幕（2-5 秒）✅ 已優化
    │   └── Slow Path: 下載音頻 → Whisper 轉錄（30-60 分鐘/小時）❌ 瓶頸
    │
    ├── 音頻檔案場景
    │   ├── 寫入暫存檔
    │   ├── 判斷是否需要 chunking（>90 秒自動啟用）
    │   ├── 若需 chunking: 分割音頻 → 逐段轉錄 → 合併結果
    │   └── 若不需: 直接呼叫 WhisperModel.transcribe()
    │
    └── 視頻檔案場景
        ├── 寫入暫存檔
        ├── ffmpeg 提取音頻（WAV/PCM, 16kHz, Mono）
        └── 同音頻檔案流程
```

### 1.2 瓶頸識別

| 階段 | 預估耗時（1 小時音頻，base 模型，CPU） | 瓶頸程度 |
|------|--------------------------------------|---------|
| 檔案上傳/下載 | 1-5 分鐘 | 🟡 中 |
| 音頻提取（視頻場景） | 30 秒-2 分鐘 | 🟢 低 |
| 模型載入（首次） | 5-30 秒 | 🟢 低（快取後無影響） |
| **Whisper 轉錄** | **30-50 分鐘** | 🔴 **主要瓶頸** |
| Chunking 分割/合併 | 1-3 分鐘 | 🟡 中 |
| 結果格式化 | <1 秒 | 🟢 低 |

### 1.3 目前使用的預設設定

| 設定 | 目前值 | 說明 |
|------|--------|------|
| `WHISPER_MODEL` | `base` | 模型大小 |
| `WHISPER_DEVICE` | `cpu` | 計算設備 |
| `WHISPER_COMPUTE_TYPE` | `int8` | 計算精度 |
| `WHISPER_CPU_THREADS` | 4（預設） | CPU 執行緒數 |
| `vad_filter` | `True` | VAD 過濾 |
| `beam_size` | **5**（chunking 硬編碼） | Beam search 大小 |
| `temperature` | **0.0**（chunking 硬編碼） | 採樣溫度 |
| `chunk_duration` | 60 秒 | 每段長度 |
| `chunk_overlap` | 2 秒 | 重疊長度 |
| `auto_enable_threshold` | 90 秒 | 自動啟用 chunking 閾值 |
| `CONCURRENT_MAX_REQUESTS` | 3 | 最大並行請求數 |

### 1.4 目前實作的優化

| 優化項 | 狀態 | 說明 |
|--------|------|------|
| 模型快取（LRU, 最多 3 個） | ✅ 已實作 | `ModelCache` 類別，避免重複載入 |
| YouTube 字幕優先 | ✅ 已實作 | 有字幕時 2-5 秒完成 |
| VAD 過濾 | ✅ 已實作 | 減少非語音段落處理 |
| 長音檔 chunking | ✅ 已實作 | 分割為 60 秒段落 |
| fast_mode 選項 | ✅ 已實作 | 增加 CPU 執行緒到 8，降低音頻品質 |
| 音頻預處理優化 | ✅ 已實作 | 16kHz, Mono, WAV/PCM |
| 並行請求控制 | ✅ 已實作 | 最多 3 個並行請求 |

### 1.5 已變更但未涉及 Whisper 優化

| 檔案 | 變更內容 | 影響 |
|------|---------|------|
| `pyproject.toml` | `pymupdf>=1.23.0,<1.25.0` → `pymupdf>=1.23.0` | 解除 PyMuPDF 版本上限，與 Whisper 無關 |

---

## 二、深度程式碼審查 — 發現的問題

### 2.1 🔴 問題 1：chunking 序列處理（主要瓶頸）

**檔案：** `api/whisper_transcribe.py:905-914`

```python
# 目前：逐段序列處理
for chunk in chunks:
    result = transcribe_chunk(
        chunk=chunk,
        model=model,
        language=None if language == "auto" else language,
        beam_size=5,          # ← 硬編碼，無法調整
        vad_filter=vad_enabled,
        temperature=0.0,      # ← 硬編碼，無法調整
    )
    chunk_results.append(result)
```

**問題：**
- 每個 chunk 依序處理，無法利用多核心並行
- 60 秒 chunk 若有 10 段，總時間 = 10 × 單段時間
- `beam_size=5` 和 `temperature=0.0` 硬編碼，無法透過 API 調整

**影響：** 長音檔（如 1 小時 = 60 個 chunk）處理時間線性增長

### 2.2 🔴 問題 2：`transcribe_audio()` 未使用 beam_size 參數

**檔案：** `api/whisper_transcribe.py:238-244`

```python
segments, info = model.transcribe(
    audio_path,
    language=actual_language,
    word_timestamps=word_timestamps,
    vad_filter=vad_enabled,
    vad_parameters=vad_params if vad_enabled else None
    # ← 沒有 beam_size 參數！使用預設值 5
    # ← 沒有 temperature 參數！使用預設值 0.0
)
```

**問題：** `transcribe_audio()` 函數沒有暴露 `beam_size` 和 `temperature` 參數，使用者無法調整。

### 2.3 🟡 問題 3：CPU 執行緒數預設偏低

**檔案：** `api/constants.py:94`

```python
DEFAULT_CPU_THREADS = 4  # 預設 4 執行緒
```

**問題：** 現代伺服器通常有 8+ 核心，預設 4 執行緒未充分利用硬體。

### 2.4 🟡 問題 4：VAD 參數可進一步優化

**檔案：** `api/constants.py:81-83`

```python
DEFAULT_VAD_MIN_SILENCE_MS = 300
DEFAULT_VAD_THRESHOLD = 0.6
DEFAULT_VAD_SPEECH_PAD_MS = 200
```

**問題：** 對於會議錄音、訪談等含大量沉默的音頻，可以更積極過濾。

### 2.5 🟡 問題 5：API 端點未暴露優化參數

**檔案：** `api/main.py:648-654`

```python
@api_router.post("/convert/audio")
async def transcribe_audio_file(
    file: UploadFile = File(...),
    language: str = Query("zh"),
    model_size: str = Query("base"),
    return_format: str = Query("markdown"),
    include_timestamps: bool = Query(False)
    # ← 沒有 beam_size
    # ← 沒有 temperature
    # ← 沒有 quality_mode
    # ← 沒有 auto model selection
):
```

**問題：** API 端點缺少效能優化相關參數。

### 2.6 🟢 問題 6：模型選擇邏輯存在但未啟用

**檔案：** `api/whisper_transcribe.py:131-147`

```python
def get_recommended_model(duration_seconds: float) -> str:
    if duration_seconds < 120:
        return "tiny"
    elif duration_seconds < 600:
        return "base"
    elif duration_seconds < 1800:
        return "small"
    return "medium"
```

**問題：** 邏輯已實作但 API 端點未呼叫，使用者仍需手動指定模型。

---

## 三、優化方案總覽

以下方案按**實施難度由低到高**排列，可**獨立實施**或**組合實施**以獲得疊加效果。

| 方案 | 優化維度 | 預估加速 | 實施難度 | 預估工時 |
|------|---------|---------|---------|---------|
| **1** | 引數調優（beam_size、CPU 執行緒、VAD） | 1.5-3x | 極低 | 1-2 小時 |
| **2** | API 參數暴露（quality_mode、auto model） | 1.5-2x | 低 | 2-3 小時 |
| **3** | 並行 chunking | 2-3x | 中 | 3-5 小時 |
| **4** | BatchedInferencePipeline | 3-5x | 中 | 4-7 小時 |
| **5** | GPU 部署 | 4-8x | 中高 | 4-8 小時 |
| **6** | 混合策略 | 10-15x | 高 | 8-15 小時 |

---

## 四、方案 1：引數調優（最小改動）

### 4.1 概述

透過修改常數和預設值，**最小程式碼改動**即可獲得顯著加速。

### 4.2 具體調整

#### 4.2.1 增加 CPU 執行緒數

**檔案：** `api/constants.py:94`

```diff
- DEFAULT_CPU_THREADS = 4
+ DEFAULT_CPU_THREADS = 8
```

**預期效果：** CPU 環境下 **1.5-2x 加速**

**原理：** CTranslate2 使用 OpenMP 並行化，執行緒數增加可近線性提升速度。

#### 4.2.2 降低 chunking 的 beam_size

**檔案：** `api/whisper_transcribe.py:911`

```diff
  result = transcribe_chunk(
      chunk=chunk,
      model=model,
      language=None if language == "auto" else language,
-     beam_size=5,
+     beam_size=1,
      vad_filter=vad_enabled,
      temperature=0.0,
  )
```

**預期效果：** **2-3x 加速**（beam search → 貪婪解碼）

**準確率影響：** WER 增加約 1-3%，一般場景可接受。

#### 4.2.3 優化 VAD 參數

**檔案：** `api/constants.py:81-83`

```diff
- DEFAULT_VAD_MIN_SILENCE_MS = 300
+ DEFAULT_VAD_MIN_SILENCE_MS = 500
- DEFAULT_VAD_THRESHOLD = 0.6
+ DEFAULT_VAD_THRESHOLD = 0.5
- DEFAULT_VAD_SPEECH_PAD_MS = 200
+ DEFAULT_VAD_SPEECH_PAD_MS = 300
```

**預期效果：** 對含大量沉默的音檔額外減少 **10-20% 處理時間**

### 4.3 綜合效果

| 調整項 | 單獨效果 | 疊加效果 |
|--------|---------|---------|
| CPU 執行緒 4→8 | 1.5-2x | |
| beam_size 5→1 | 2-3x | |
| VAD 優化 | 1.1-1.2x | |
| **組合效果** | | **2-4x** |

### 4.4 風險評估

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| beam_size=1 降低準確率 | WER 增加 1-3% | 可保留為可選參數 |
| VAD 過於積極可能過濾語音 | 遺漏輕聲/快速語音 | 保留預設 VAD 參數作為 fallback |
| CPU 執行緒過多影響並行請求 | 請求互相干擾 | 監控 CPU 使用率 |

### 4.5 預估工時

| 項目 | 工時 |
|------|------|
| 修改 constants.py | 0.5 小時 |
| 修改 whisper_transcribe.py | 0.5 小時 |
| 測試驗證 | 1 小時 |
| **總計** | **2 小時** |

---

## 五、方案 2：API 參數暴露

### 5.1 概述

在 API 端點新增效能優化參數，讓使用者可根據需求調整速度/品質平衡。

### 5.2 具體調整

#### 5.2.1 新增 `beam_size` 參數

**檔案：** `api/main.py` — `/convert/audio` 端點

```python
@api_router.post("/convert/audio")
async def transcribe_audio_file(
    file: UploadFile = File(...),
    language: str = Query("zh"),
    model_size: str = Query("base"),
    return_format: str = Query("markdown"),
    include_timestamps: bool = Query(False),
    beam_size: int = Query(5, description="Beam search size (1=faster, 5=balanced, 10=quality)"),
    temperature: float = Query(0.0, description="Sampling temperature (0.0=greedy, 1.0=creative)"),
):
```

#### 5.2.2 新增 `quality_mode` 預設模式

```python
QUALITY_PRESETS = {
    "speed": {"beam_size": 1, "temperature": 0.0, "model": None},
    "balanced": {"beam_size": 3, "temperature": 0.0, "model": None},
    "quality": {"beam_size": 5, "temperature": 0.0, "model": None},
}

quality_mode: str = Query("balanced", description="Quality preset: speed, balanced, quality")
```

#### 5.2.3 啟用自動模型選擇

將 `model_size` 預設值改為 `"auto"`：

```python
model_size: str = Query("auto", description="Model size (auto, tiny, base, small, medium, large)")

# 若 model_size="auto"，根據音檔長度自動選擇
if model_size == "auto":
    duration = get_audio_duration(tmp_path)
    model_size = get_recommended_model(duration)
```

### 5.3 預估效果

| 場景 | 目前（固定 base, beam=5） | 優化後 | 加速比 |
|------|------------------------|--------|--------|
| 30 秒短音檔 | 5 秒 | 3 秒（tiny + beam=1） | **1.7x** |
| 5 分鐘音檔 | 25 秒 | 25 秒（base, balanced） | 1.0x |
| 30 分鐘音檔 | 150 秒 | 120 秒（small + beam=1） | **1.25x** |

### 5.4 預估工時

| 項目 | 工時 |
|------|------|
| 修改 API 端點（3 個） | 1-2 小時 |
| 修改 whisper_transcribe.py 支援參數 | 1 小時 |
| 測試驗證 | 1 小時 |
| **總計** | **3-4 小時** |

---

## 六、方案 3：並行 chunking

### 6.1 概述

目前的 chunking 是**序列處理**（逐段轉錄），改為**並行處理**可加速 2-3 倍。

### 6.2 目前實作（序列處理）

**檔案：** `api/whisper_transcribe.py:905-914`

```python
# 目前：逐段序列處理
for chunk in chunks:
    result = transcribe_chunk(chunk=chunk, model=model, ...)
    chunk_results.append(result)
```

### 6.3 優化方案（並行處理）

```python
import concurrent.futures

def transcribe_audio_chunked(...):
    # ... 前面邏輯不變 ...

    # 並行處理 chunks
    max_workers = min(4, len(chunks))  # 最多 4 個並行
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                transcribe_chunk,
                chunk=chunk,
                model=model,
                language=None if language == "auto" else language,
                beam_size=1,
                vad_filter=vad_enabled,
                temperature=0.0,
            ): chunk
            for chunk in chunks
        }
        for future in concurrent.futures.as_completed(futures):
            chunk_results.append(future.result())
```

### 6.4 注意事項

| 風險 | 說明 | 緩解措施 |
|------|------|---------|
| CPU 記憶體壓力 | 並行處理增加記憶體使用 | 限制 max_workers=2-4 |
| GPU VRAM 限制 | 多個並行轉錄可能超出 VRAM | GPU 環境應使用方案 4（BatchedInferencePipeline） |
| 結果順序 | 並行完成順序不固定 | `merge_transcription_results()` 已使用 timestamp 排序 |

### 6.5 預估效果

| 硬體 | 目前（序列） | 並行（4 workers） | 加速比 |
|------|------------|-----------------|--------|
| CPU（8 核心） | 30 分鐘 | 10-15 分鐘 | **2-3x** |
| GPU | 不適用（應使用 BatchedInferencePipeline） | | |

### 6.6 預估工時

| 項目 | 工時 |
|------|------|
| 修改 whisper_transcribe.py | 2-3 小時 |
| 測試驗證 | 1-2 小時 |
| **總計** | **3-5 小時** |

---

## 七、方案 4：BatchedInferencePipeline

### 7.1 概述

faster-whisper 提供 `BatchedInferencePipeline`，將音頻分段後**並行處理**，可獲得 **3-5x 加速**。這是比手動並行 chunking 更優雅的方案。

### 7.2 技術原理

```
標準模式（WhisperModel）:
音頻 → 分段1 → 轉錄 → 分段2 → 轉錄 → 分段3 → 轉錄 → 合併（序列處理）

Batched 模式:
音頻 → VAD 分段 → [分段1, 分段2, 分段3] → 並行轉錄 → 合併（並行處理）
```

### 7.3 官方基準數據

**13 分鐘音頻，large-v2，RTX 3070 Ti：**

| 配置 | 時間 | VRAM | 加速比 |
|------|------|------|--------|
| 標準 (fp16) | 63 秒 | 4525MB | 1.0x |
| Batched (fp16, batch=8) | 17 秒 | 6090MB | **3.7x** |
| Batched (int8, batch=8) | 16 秒 | 4500MB | **3.9x** |

**CPU（Intel i7-12700K, 8 執行緒, small 模型）：**

| 配置 | 時間 | RAM | 加速比 |
|------|------|-----|--------|
| 標準 (fp32) | 157 秒 | 2257MB | 1.0x |
| Batched (batch=8) | 66 秒 | 4230MB | **2.4x** |

### 7.4 實施細節

#### 7.4.1 修改模型載入

```python
# api/whisper_transcribe.py
from faster_whisper import WhisperModel, BatchedInferencePipeline

def get_model(
    model_size: Optional[str] = None,
    device: Optional[str] = None,
    compute_type: Optional[str] = None,
    cpu_threads: int = 4,
    use_batched: bool = False,
):
    cache_key = f"{model_size}_{device}_{compute_type}_{cpu_threads}_{'batched' if use_batched else 'standard'}"

    model = _model_cache.get(cache_key)
    if model is None:
        base_model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=cpu_threads,
        )
        if use_batched:
            model = BatchedInferencePipeline(model=base_model)
        else:
            model = base_model
        _model_cache.set(cache_key, model)

    return model
```

#### 7.4.2 修改轉錄函數

```python
def transcribe_audio(
    audio_path: str,
    language: str = "auto",
    model_size: Optional[str] = None,
    device: Optional[str] = None,
    compute_type: Optional[str] = None,
    cpu_threads: Optional[int] = None,
    vad_enabled: bool = True,
    vad_params: Optional[dict] = None,
    word_timestamps: bool = False,
    use_batched: bool = True,
    batch_size: int = 8,
):
    # ... 現有邏輯 ...

    model = get_model(effective_model, effective_device, effective_compute_type,
                      cpu_threads=effective_threads, use_batched=use_batched)

    if use_batched:
        segments, info = model.transcribe(
            audio_path,
            language=actual_language,
            word_timestamps=word_timestamps,
            vad_filter=vad_enabled,
            vad_parameters=vad_params if vad_enabled else None,
            batch_size=batch_size,
            chunk_length_s=30,
        )
    else:
        segments, info = model.transcribe(
            audio_path,
            language=actual_language,
            word_timestamps=word_timestamps,
            vad_filter=vad_enabled,
            vad_parameters=vad_params if vad_enabled else None,
        )
```

#### 7.4.3 簡化 chunking 邏輯

由於 BatchedInferencePipeline 已內建分段處理，可簡化手動 chunking：

```python
def transcribe_audio_chunked(..., use_batched: bool = True, batch_size: int = 8):
    if use_batched:
        # 直接使用 BatchedInferencePipeline，跳過手動 chunking
        return transcribe_audio(
            audio_path, language=language, model_size=model_size,
            device=device, compute_type=compute_type,
            cpu_threads=cpu_threads, vad_enabled=vad_enabled,
            vad_params=vad_params, word_timestamps=word_timestamps,
            use_batched=True, batch_size=batch_size,
        )
    # 否則使用原有的手動 chunking 邏輯（CPU fallback）
```

### 7.5 注意事項

| 限制 | 說明 | 影響 |
|------|------|------|
| 不支援 `condition_on_previous_text` | 長音檔上下文連貫性可能略降 | 一般場景影響小 |
| 不支援 `initial_prompt` | 無法提供自訂詞彙提示 | 評估是否需要 |
| VAD 自動啟用 | Batched 模式預設啟用 VAD | 與現有邏輯一致 |

### 7.6 預估效果

| 場景 | 目前時間 | 優化後時間 | 加速比 |
|------|---------|-----------|--------|
| 1 小時音頻，base，CPU | ~30 分鐘 | ~12-15 分鐘 | **2-2.5x** |
| 1 小時音頻，base，GPU | ~8 分鐘 | ~2-3 分鐘 | **3-4x** |
| 1 小時音頻，large-v3，GPU | ~15 分鐘 | ~3-4 分鐘 | **3.7-5x** |

### 7.7 預估工時

| 項目 | 工時 |
|------|------|
| 修改 whisper_transcribe.py | 2-3 小時 |
| 修改 chunking 邏輯 | 1-2 小時 |
| 測試驗證 | 1-2 小時 |
| **總計** | **4-7 小時** |

---

## 八、方案 5：GPU 部署

### 8.1 概述

從 CPU 改為 GPU 部署，可獲得 **4-8x 加速**。

### 8.2 硬體需求

| GPU | VRAM | 支援模型 | 預估價格 |
|-----|------|---------|---------|
| NVIDIA T4 | 16GB | 最大 large-v3 | ~$1,200 |
| NVIDIA RTX 3060 | 12GB | 最大 large-v3 | ~$300 |
| NVIDIA RTX 4060 | 8GB | 最大 medium | ~$300 |
| NVIDIA L4 | 24GB | 最大 large-v3 | ~$2,000 |
| NVIDIA A10G | 24GB | 最大 large-v3 | ~$3,500 |

### 8.3 Docker 配置

```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - WHISPER_DEVICE=cuda
      - WHISPER_COMPUTE_TYPE=float16
```

```dockerfile
# Dockerfile - 使用 NVIDIA CUDA 基礎映像
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04
```

### 8.4 預估效果

| 場景 | CPU 時間 | GPU 時間 | 加速比 |
|------|---------|---------|--------|
| 1 分鐘，base | 5 秒 | 1 秒 | **5x** |
| 10 分鐘，base | 50 秒 | 10 秒 | **5x** |
| 1 小時，base | 5 分鐘 | 1 分鐘 | **5x** |
| 1 小時，large-v3 | 15 分鐘 | 2-3 分鐘 | **5-7x** |

### 8.5 預估工時

| 項目 | 工時 |
|------|------|
| 修改 Dockerfile（CUDA 基礎映像） | 1-2 小時 |
| 修改 docker-compose.yml | 0.5 小時 |
| 安裝 NVIDIA Container Toolkit | 1 小時 |
| 環境變數調整 | 0.5 小時 |
| 測試驗證 | 1-2 小時 |
| **總計** | **4-6 小時** |

---

## 九、方案 6：混合策略（最佳化組合）

### 9.1 概述

結合前述所有方案，根據硬體和使用場景動態選擇最佳策略。

### 9.2 架構設計

```
API Request
    │
    ├── 音檔分析
    │   ├── 獲取時長
    │   ├── 獲取檔案大小
    │   └── 判斷是否有語音（快速 VAD 預檢）
    │
    ├── 策略選擇
    │   ├── GPU 可用？
    │   │   ├── 是 → BatchedInferencePipeline + float16 + batch_size=8
    │   │   └── 否 → CPU 優化路徑
    │   │
    │   ├── 音檔時長
    │   │   ├── < 2 分鐘 → tiny 模型
    │   │   ├── 2-10 分鐘 → base 模型
    │   │   └── > 10 分鐘 → 動態選擇（small/medium）
    │   │
    │   └── quality_mode 參數
    │       ├── speed → beam_size=1, int8
    │       ├── balanced → beam_size=3, int8
    │       └── quality → beam_size=5, float32
    │
    └── 執行轉錄
        ├── GPU: BatchedInferencePipeline（並行處理）
        └── CPU: 並行 chunking + 優化參數
```

### 9.3 推薦配置組合

#### 9.3.1 GPU 環境（推薦）

| 設定 | 值 | 說明 |
|------|-----|------|
| 設備 | `cuda` | GPU 加速 |
| 計算型別 | `float16` | GPU 最佳精度 |
| 處理模式 | `BatchedInferencePipeline` | 並行處理 |
| batch_size | `8` | 平衡速度和記憶體 |
| beam_size | `3` | 平衡準確率和速度 |
| VAD | `True` | 過濾非語音段落 |
| chunk_length_s | `30` | Batched 模式分段長度 |

#### 9.3.2 CPU 環境（目前預設）

| 設定 | 值 | 說明 |
|------|-----|------|
| 設備 | `cpu` | CPU 處理 |
| 計算型別 | `int8` | CPU 最佳化 |
| cpu_threads | `8` | 增加執行緒數 |
| 處理模式 | 並行 chunking | 4 workers |
| beam_size | `1` | 貪婪解碼加速 |
| VAD | `True`（積極模式） | 最大化過濾 |

### 9.4 預估效果

| 場景 | 目前時間 | 優化後時間（GPU） | 優化後時間（CPU） | GPU 加速比 | CPU 加速比 |
|------|---------|-----------------|-----------------|-----------|-----------|
| 1 分鐘，base | 5 秒 | 1 秒 | 2 秒 | **5x** | **2.5x** |
| 10 分鐘，base | 50 秒 | 10 秒 | 20 秒 | **5x** | **2.5x** |
| 1 小時，base | 5 分鐘 | 1 分鐘 | 2 分鐘 | **5x** | **2.5x** |
| 1 小時，large-v3 | 15 分鐘 | 3 分鐘 | 8 分鐘 | **5x** | **1.9x** |

### 9.5 預估工時

| 項目 | 工時 |
|------|------|
| 策略配置系統 | 2-3 小時 |
| BatchedInferencePipeline 整合 | 3-5 小時 |
| 並行 chunking 實作 | 2-3 小時 |
| 動態模型選擇 | 1-2 小時 |
| API 端點更新 | 1-2 小時 |
| 測試驗證 | 3-4 小時 |
| **總計** | **12-19 小時** |

---

## 十、方案比較總表

### 10.1 效果比較

| 方案 | CPU 加速 | GPU 加速 | 準確率影響 | 記憶體影響 | 實施難度 | 程式碼改動 |
|------|---------|---------|-----------|-----------|---------|-----------|
| 1. 引數調優 | 1.5-3x | 1.5-2x | 輕微（beam_size） | 無 | ⭐ | 3 行 |
| 2. API 參數暴露 | 1.5-2x | 1.5-2x | 可配置 | 無 | ⭐⭐ | ~50 行 |
| 3. 並行 chunking | 2-3x | N/A | 無 | +50% RAM | ⭐⭐ | ~20 行 |
| 4. BatchedInferencePipeline | 2-2.5x | 3-5x | 輕微 | +40% VRAM | ⭐⭐⭐ | ~100 行 |
| 5. GPU 部署 | N/A | 4-8x | 無 | 需要 GPU | ⭐⭐⭐ | Docker 配置 |
| 6. 混合策略 | 5-10x | 10-15x | 可配置 | 可配置 | ⭐⭐⭐⭐ | ~200 行 |

### 10.2 組合效果矩陣

| 組合 | 預估加速（CPU） | 預估加速（GPU） | 實施難度 |
|------|---------------|---------------|---------|
| 方案 1 + 2 | 2-4x | 2-3x | 低 |
| 方案 1 + 3 | 3-5x | 3-5x | 中 |
| 方案 1 + 2 + 3 | 3-6x | 3-5x | 中 |
| 方案 1 + 2 + 4 | 3-5x | 5-8x | 中高 |
| 方案 1 + 2 + 3 + 5 | 5-10x | 5-8x | 中高 |
| 方案 1 + 2 + 4 + 5 | 3-5x | 8-12x | 中 |
| **方案 1 + 2 + 3 + 4 + 5** | **5-10x** | **10-15x** | **高** |

---

## 十一、實施建議路徑

### 11.1 階段式實施

建議分三階段實施，每階段獨立驗證效果後再進入下一阶段：

#### 第一階段：快速見效（1-2 天）

**目標：** 最小改動，快速獲得 2-3x 加速

- [ ] 方案 1：引數調優（CPU 執行緒、beam_size、VAD）
- [ ] 方案 2：API 參數暴露（quality_mode、auto model）

**預估效果：** CPU 2-4x，GPU 2-3x
**預估工時：** 4-6 小時
**程式碼改動量：** ~50 行

#### 第二階段：架構優化（3-5 天）

**目標：** 引入 BatchedInferencePipeline 或並行 chunking

- [ ] 方案 4：BatchedInferencePipeline 整合（GPU 優先）
- [ ] 方案 3：並行 chunking（CPU fallback）

**預估效果：** CPU 3-5x，GPU 5-8x
**預估工時：** 7-12 小時
**程式碼改動量：** ~120 行

#### 第三階段：硬體升級（可選，1-2 週）

**目標：** GPU 部署 + 混合策略

- [ ] 方案 5：GPU 部署
- [ ] 方案 6：混合策略整合

**預估效果：** CPU 5-10x，GPU 10-15x
**預估工時：** 12-19 小時

### 11.2 立即可做（最小改動）

以下調整**只需修改 3 行程式碼**，立即生效：

**Step 1：** `api/constants.py`
```diff
- DEFAULT_CPU_THREADS = 4
+ DEFAULT_CPU_THREADS = 8
- DEFAULT_VAD_MIN_SILENCE_MS = 300
+ DEFAULT_VAD_MIN_SILENCE_MS = 500
- DEFAULT_VAD_THRESHOLD = 0.6
+ DEFAULT_VAD_THRESHOLD = 0.5
- DEFAULT_VAD_SPEECH_PAD_MS = 200
+ DEFAULT_VAD_SPEECH_PAD_MS = 300
```

**Step 2：** `api/whisper_transcribe.py:911`
```diff
- beam_size=5,
+ beam_size=1,
```

**預估效果：2-3x 加速，改動 5 行程式碼。**

---

## 十二、效能監控建議

### 12.1 新增處理時間指標

```python
# 在 metadata 中新增詳細時間指標
metadata = {
    "processing_time_ms": total_time,
    "model_load_time_ms": model_load_time,
    "transcription_time_ms": transcribe_time,
    "chunking_time_ms": chunking_time,
    "merging_time_ms": merging_time,
    "vad_filtered_duration": vad_filtered,
    "realtime_factor": realtime_factor,
}
```

### 12.2 建議監控指標

| 指標 | 說明 | 閾值 |
|------|------|------|
| Real-time Factor | 處理時間 / 音頻時長 | CPU < 0.5x, GPU < 0.2x |
| 模型載入時間 | 首次請求延遲 | < 30 秒 |
| 快取命中率 | 模型快取命中比例 | > 80% |
| VAD 過濾率 | 被過濾的音頻比例 | 20-60%（正常） |
| 錯誤率 | 轉錄失敗比例 | < 1% |

---

## 十三、總結

### 13.1 最佳投資回報比

| 排名 | 方案 | 加速比 | 工時 | 改動量 | 投資回報 |
|------|------|--------|------|--------|---------|
| 🥇 | 方案 1：引數調優 | 1.5-3x | 2h | 5 行 | **最高** |
| 🥈 | 方案 2：API 參數暴露 | 1.5-2x | 3-4h | ~50 行 | 高 |
| 🥉 | 方案 3：並行 chunking | 2-3x | 3-5h | ~20 行 | 高 |
| 4 | 方案 4：BatchedInferencePipeline | 3-5x | 4-7h | ~100 行 | 中高 |
| 5 | 方案 5：GPU 部署 | 4-8x | 4-6h | Docker | 中（需硬體成本） |

### 13.2 推薦實施順序

1. **立即執行**：方案 1（引數調優）— 2 小時，5 行改動，零風險
2. **短期執行**：方案 2（API 參數暴露）— 3-4 小時，低風險
3. **中期執行**：方案 3 + 4（並行 chunking + BatchedInferencePipeline）— 7-12 小時
4. **長期評估**：方案 5（GPU 部署）— 需評估硬體成本

### 13.3 預期總效果

若完整實施方案 1+2+3：
- **CPU 環境：3-6x 加速**
- **GPU 環境：3-5x 加速**

若完整實施所有方案（含 GPU）：
- **CPU 環境：5-10x 加速**
- **GPU 環境：10-15x 加速**

### 13.4 與前次報告的差異

| 項目 | 前次報告 | 本次更新 | 差異原因 |
|------|---------|---------|---------|
| 方案數量 | 6 個 | 6 個（拆分方案 1、2） | 更精細的粒度 |
| 方案 1 工時 | 1-2h | 2h | 更準確的估算 |
| 方案 2 工時 | 3-4h（原方案 3） | 3-4h | 獨立為新方案 |
| 程式碼改動量 | 未標註 | 每方案標註 | 便於評估成本 |
| 問題識別 | 概括性 | 6 個具體問題 | 基於實際程式碼審查 |
