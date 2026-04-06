# Whisper 升級方案詳細分析

> **Date:** 2026-04-05  
> **Author:** Kimhsiao  
> **Purpose:** 提供三種推薦升級方案的深度分析，包含技術細節、硬體需求、效能評估與實施步驟

---

## 目錄

- [方案 A：升級 faster-whisper + 啟用 BatchedInferencePipeline](#方案-a升級-faster-whisper--啟用-batchedinferencepipeline)
- [方案 B：使用 distil-whisper 模型](#方案-b使用-distil-whisper-模型)
- [方案 C：整合 whisperX](#方案-c整合-whisperx)
- [方案 D：混合策略（動態模型選擇）](#方案-d混合策略動態模型選擇)
- [方案比較總表](#方案比較總表)

---

## 方案 A：升級 faster-whisper + 啟用 BatchedInferencePipeline

### A.1 方案概述

升級 `faster-whisper` 到最新版本並啟用 `BatchedInferencePipeline`，在不改變架構的前提下獲得最佳效能提升。

### A.2 技術原理

`BatchedInferencePipeline` 是 faster-whisper 的批次推論管道，工作原理：

1. **音頻分段**：將長音頻自動分割為多個 segment
2. **批次編碼**：多個 segment 同時通過 encoder（並行處理）
3. **解碼優化**：減少重複計算，提高 GPU 利用率
4. **結果合併**：自動處理 segment 邊界，輸出連續轉錄結果

```python
from faster_whisper import WhisperModel, BatchedInferencePipeline

# 載入模型
model = WhisperModel("large-v3", device="cuda", compute_type="float16")

# 包裝為批次管道
batched_model = BatchedInferencePipeline(model=model)

# 批次轉錄
segments, info = batched_model.transcribe(
    "long_audio.mp3",
    batch_size=16,      # 並行 segment 數量
    chunk_length_s=30,  # 每段長度
    language="zh"
)
```

### A.3 效能評估

| 配置 | 速度提升 | 適用場景 |
|------|---------|---------|
| 標準 WhisperModel | 1.0x（基準） | 單一檔案 |
| BatchedInferencePipeline (batch_size=16) | **2-4x faster** | 長音檔、批次處理 |
| BatchedInferencePipeline + INT8 | **3-5x faster** | GPU 記憶體受限 |

**長音檔處理對比（1 小時音頻，large-v3，GPU）：**

| 方式 | 處理時間 | 記憶體 |
|------|---------|--------|
| 標準 transcribe() | ~15 分鐘 | ~10GB |
| BatchedInferencePipeline (batch=16) | **~4-7 分鐘** | ~16GB |
| BatchedInferencePipeline + INT8 | **~3-5 分鐘** | ~8GB |

### A.4 硬體需求

| 硬體 | 最低需求 | 推薦配置 |
|------|---------|---------|
| GPU VRAM | 8GB（FP16, batch=8） | 16GB+（FP16, batch=16） |
| CPU | 4 核心 | 8 核心+ |
| 記憶體 | 4GB | 8GB+ |
| 儲存空間 | 6GB（large-v3 模型） | 20GB（含快取） |

### A.5 軟體需求

| 套件 | 版本 | 說明 |
|------|------|------|
| `faster-whisper` | >= 1.0.0 | BatchedInferencePipeline 需要 1.0+ |
| `ctranslate2` | >= 4.0 | 隨 faster-whisper 自動安裝 |
| Python | >= 3.8 | 本專案使用 3.12 |

### A.6 實施步驟

**Step 1：升級依賴**
```diff
# pyproject.toml
dependencies = [
    # ...
-   "faster-whisper",
+   "faster-whisper>=1.0.0",
    # ...
]
```

**Step 2：修改 whisper_transcribe.py**
```python
from faster_whisper import WhisperModel, BatchedInferencePipeline

def get_model(...):
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    # 包裝為批次管道
    batched_model = BatchedInferencePipeline(model=model)
    return batched_model

def transcribe_audio(audio_path, ...):
    # 使用批次管道
    segments, info = model.transcribe(
        audio_path,
        language=actual_language,
        word_timestamps=word_timestamps,
        vad_filter=vad_enabled,
        vad_parameters=vad_params if vad_enabled else None,
        batch_size=16,        # 新增
        chunk_length_s=30,    # 新增
    )
```

**Step 3：調整 chunking 邏輯**
- BatchedInferencePipeline 已內建分段處理，可簡化或移除手動 chunking
- 保留手動 chunking 作為 fallback（CPU 環境）

### A.7 風險與注意事項

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| BatchedInferencePipeline 不支援 `condition_on_previous_text` | 長音檔上下文連貫性可能略降 | 測試驗證準確率 |
| BatchedInferencePipeline 不支援 `initial_prompt` | 無法提供自訂詞彙提示 | 評估是否需要此功能 |
| batch_size 過大導致 OOM | GPU 記憶體不足 | 動態調整 batch_size |
| CPU 環境無 BatchedInferencePipeline 加速 | CPU 環境無改善 | 保留原有邏輯作為 fallback |

### A.8 預估工時

| 項目 | 工時 |
|------|------|
| 升級依賴 | 0.5 小時 |
| 修改核心轉錄邏輯 | 2-3 小時 |
| 調整 chunking 邏輯 | 1-2 小時 |
| 測試驗證 | 2-3 小時 |
| **總計** | **5.5-8.5 小時** |

---

## 方案 B：使用 distil-whisper 模型

### B.1 方案概述

將目前的 Whisper 模型替換為 distil-whisper 的蒸餾模型，**零程式碼改動**即可獲得 6 倍加速。

### B.2 技術原理

Distil-Whisper 使用知識蒸餾技術，保留原始 Whisper 的 encoder，將 decoder 從 32 層蒸餾為 2 層：

```
Original Whisper:  Encoder (32層) + Decoder (32層) = 1.55B 參數
Distil-Whisper:    Encoder (32層，凍存) + Decoder (2層) = 756M 參數
```

- Decoder 佔據 90%+ 推論時間，減少 decoder 層數是效能關鍵
- 使用大規模 pseudo-labeling 訓練，維持準確率
- 可透過 faster-whisper 直接載入，完全相容

### B.3 可用模型

| 模型 | 參數量 | 速度（vs large-v3） | 短句 WER | 長句 WER | VRAM (FP16) | 維護狀態 |
|------|--------|---------------------|----------|----------|-------------|---------|
| **distil-large-v3** | 756M | **6.3x faster** | 9.7% | 10.8% | ~6GB | ✅ |
| **distil-large-v3.5** | 756M | ~7x faster | **7.08%** | 11.39% | ~6GB | ✅ 最新 (2025-03) |
| distil-large-v2 | 756M | 5.8x faster | 10.1% | 11.6% | ~6GB | ⚠️ 舊版 |
| distil-medium.en | 394M | 6.8x faster | 11.1% | 12.4% | ~3GB | ✅ |
| distil-small.en | 166M | 5.6x faster | 12.1% | 12.8% | ~1.5GB | ✅ |

### B.4 準確率分析

**WER（Word Error Rate）比較：**

| 測試集 | large-v3 | distil-large-v3 | distil-large-v3.5 | 差異 |
|--------|----------|-----------------|-------------------|------|
| TED-LIUM | 8.4% | 9.7% | **7.08%** | v3.5 更優 |
| Earnings21 | 10.2% | 10.5% | 9.8% | 差異 <1% |
| 平均短句 | 8.4% | 9.7% | **7.08%** | v3.5 更優 |
| 平均長句 | 11.0% | **10.8%** | 11.39% | v3 更優 |

**關鍵發現：**
- distil-large-v3 在長句轉錄上**優於** original large-v3
- distil-large-v3.5 在短句表現最佳，但長句略遜於 v3
- 所有 distil 模型都維持在 **1% WER 範圍內**

### B.5 硬體需求

| 硬體 | distil-large-v3 | distil-medium.en | distil-small.en |
|------|----------------|-----------------|----------------|
| GPU VRAM (FP16) | ~6GB | ~3GB | ~1.5GB |
| GPU VRAM (INT8) | ~3GB | ~1.5GB | ~0.8GB |
| CPU 記憶體 (INT8) | ~4GB | ~2GB | ~1GB |
| 磁碟空間 | ~3GB | ~1.5GB | ~0.8GB |

### B.6 實施步驟

**Step 1：更改模型名稱（零程式碼改動）**

```diff
# .env
-WHISPER_MODEL=base
+WHISPER_MODEL=distil-large-v3
```

或透過 API 參數：
```bash
# 使用 distil-large-v3
curl -X POST "http://localhost:51083/api/v1/convert/audio?model_size=distil-large-v3" \
  -F "file=@audio.mp3"
```

**Step 2：更新模型名稱映射（可選）**

```python
# api/constants.py 新增 distil 模型映射
MODEL_SELECTION_THRESHOLDS = {
    "tiny": 120,
    "base": 600,
    "small": 1800,
    "medium": float("inf"),
    # 新增 distil 模型
    "distil-large-v3": 600,    # 等同 base 的效能門檻
    "distil-large-v3.5": 600,
}
```

**Step 3：更新 Dockerfile 預載模型**

```diff
- RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"
+ RUN python -c "from faster_whisper import WhisperModel; WhisperModel('distil-large-v3', device='cpu', compute_type='int8')"
```

### B.7 ⚠️ 重大限制

**distil-whisper 僅支援英文！**

| 需求 | distil-whisper | 影響 |
|------|---------------|------|
| 中文轉錄 | ❌ 不支援 | 本專案核心功能 |
| 日文轉錄 | ❌ 不支援 | 本專案支援語言 |
| 韓文轉錄 | ❌ 不支援 | 本專案支援語言 |
| 泰文轉錄 | ❌ 不支援 | 本專案支援語言 |
| 越南文轉錄 | ❌ 不支援 | 本專案支援語言 |

### B.8 混合策略（英文用 distil，其他用原始模型）

```python
def get_model_for_language(language: str) -> str:
    """根據語言選擇最佳模型"""
    if language in ("en", "auto"):
        return "distil-large-v3"  # 英文用 distil 加速
    else:
        return "large-v3"  # 其他語言用原始模型
```

### B.9 預估工時

| 項目 | 工時 |
|------|------|
| 僅更改模型名稱 | **0.5 小時** |
| 完整混合策略（語言判斷） | 2-3 小時 |
| 測試驗證 | 1-2 小時 |
| **總計（僅英文）** | **0.5 小時** |
| **總計（混合策略）** | **3.5-5.5 小時** |

---

## 方案 C：整合 whisperX

### C.1 方案概述

將目前的 faster-whisper 替換為 whisperX，獲得更精準的字級時間戳和說話者分離功能。

### C.2 技術原理

whisperX 在 faster-whisper 基礎上增加兩層：

1. **Wav2Vec2 字級對齊**：使用預訓練的 Wav2Vec2 模型對齊 whisper 輸出，獲得更精準的 word-level timestamps
2. **Speaker Diarization**：使用 pyannote-audio 自動識別不同說話者

```
音頻輸入 → faster-whisper 轉錄 → Wav2Vec2 對齊 → 說話者分離 → 最終輸出
```

### C.3 功能比較

| 功能 | faster-whisper | whisperX | 差異 |
|------|---------------|----------|------|
| 核心轉錄 | ✅ | ✅（基於 faster-whisper） | 相同 |
| 字級時間戳 | ✅（whisper 原生） | ✅（Wav2Vec2 對齊） | **whisperX 更精準** |
| 說話者分離 | ❌ | ✅ | **whisperX 獨有** |
| VAD 過濾 | ✅ | ✅ | 相同 |
| 量化支援 | ✅ | ✅ | 相同 |
| distil 模型 | ✅ | ✅ | 可搭配使用 |
| 多語言 | ✅ | ✅ | 相同 |

### C.4 效能評估

| 配置 | 處理時間（1 小時音頻） | 額外開銷 |
|------|----------------------|---------|
| faster-whisper (large-v3, GPU) | ~15 分鐘 | 基準 |
| whisperX (large-v3 + Wav2Vec2) | ~18 分鐘 | +20%（對齊） |
| whisperX (+ Speaker Diarization) | ~22 分鐘 | +47%（含說話者分離） |
| whisperX + distil-large-v3 | **~3 分鐘** | 包含對齊 |

### C.5 硬體需求

| 硬體 | 最低需求 | 推薦配置 |
|------|---------|---------|
| GPU VRAM | 8GB（含 Wav2Vec2 模型） | 16GB+（含說話者分離） |
| CPU 記憶體 | 8GB | 16GB+ |
| 儲存空間 | 10GB（含額外模型） | 30GB |

### C.6 軟體需求

| 套件 | 版本 | 說明 |
|------|------|------|
| `whisperx` | latest | 核心套件 |
| `faster-whisper` | >= 1.0 | whisperX 依賴 |
| `pyannote-audio` | >= 3.1 | 說話者分離（需要 HuggingFace token） |
| `torch` | >= 2.0 | 深度學習框架 |
| Python | >= 3.10 | 本專案使用 3.12 |

### C.7 實施步驟

**Step 1：新增依賴**
```diff
# pyproject.toml
dependencies = [
    # ...
    "faster-whisper>=1.0.0",
+   "whisperx>=3.1.0",
+   "pyannote-audio>=3.1.0",  # 可選：說話者分離
    # ...
]
```

**Step 2：修改 whisper_transcribe.py**
```python
import whisperx

def transcribe_audio_with_whisperx(audio_path, language="auto", ...):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # 1. 核心轉錄（與 faster-whisper 相同 API）
    model = whisperx.load_model("large-v3", device, compute_type="float16")
    audio = whisperx.load_audio(audio_path)
    result = model.transcribe(audio, batch_size=16, language=language)
    
    # 2. Wav2Vec2 對齊（可選）
    if language in ["en", "zh", "ja", "ko"]:  # 僅部分語言支援
        model_a, metadata = whisperx.load_align_model(
            language_code=result["language"], device=device
        )
        result = whisperx.align(
            result["segments"], model_a, metadata, audio, device
        )
    
    # 3. 說話者分離（可選）
    # diarize_model = whisperx.DiarizationPipeline(use_auth_token=token, device=device)
    # diarize_segments = diarize_model(audio)
    # result = whisperx.assign_word_speakers(diarize_segments, result)
    
    return result
```

**Step 3：更新 API 端點**
```python
# 新增 whisperx 模式參數
@router.post("/convert/audio")
async def transcribe_audio(
    file: UploadFile,
    engine: str = "faster-whisper",  # "faster-whisper" | "whisperx"
    enable_diarization: bool = False,  # 說話者分離
    ...
):
    if engine == "whisperx":
        result = transcribe_audio_with_whisperx(...)
    else:
        result = transcribe_audio(...)
```

### C.8 風險與注意事項

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| Wav2Vec2 對齊不支援所有語言 | 中文/泰文/越南文可能無法對齊 | 僅在支援語言時啟用對齊 |
| pyannote-audio 需要 HuggingFace token | 說話者分離需要額外設定 | 設為可選功能 |
| Docker 大小增加 | 額外模型增加映像大小 | 使用多階段構建 |
| 記憶體需求增加 | Wav2Vec2 模型需要額外 VRAM | 提供 CPU fallback |

### C.9 預估工時

| 項目 | 工時 |
|------|------|
| 新增依賴和 Docker 更新 | 1-2 小時 |
| 整合 whisperX 核心轉錄 | 2-3 小時 |
| 實作 Wav2Vec2 對齊 | 1-2 小時 |
| 實作說話者分離（可選） | 2-3 小時 |
| API 端點更新 | 1-2 小時 |
| 測試驗證 | 2-3 小時 |
| **總計（僅對齊）** | **7-12 小時** |
| **總計（含說話者分離）** | **9-15 小時** |

---

## 方案 D：混合策略（動態模型選擇）

### D.1 方案概述

結合方案 A、B、C 的優勢，根據語言、硬體和效能需求動態選擇最佳轉錄策略。

### D.2 架構設計

```
API Request
    │
    ├── 語言判斷
    │   ├── 英文 → distil-large-v3.5（6x 加速）
    │   └── 其他語言 → large-v3（多語言支援）
    │
    ├── 硬體判斷
    │   ├── GPU + BatchedInferencePipeline → 批次處理
    │   ├── GPU 標準 → 標準推理
    │   └── CPU → INT8 量化 + 手動 chunking
    │
    └── 功能需求
        ├── 需要說話者分離 → whisperX
        ├── 需要精準字級時間戳 → whisperX + Wav2Vec2
        └── 標準轉錄 → faster-whisper
```

### D.3 實施步驟

**Step 1：新增策略配置**
```python
# api/transcription_config.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class TranscriptionStrategy:
    """動態轉錄策略配置"""
    model: str                  # 模型名稱
    engine: str                 # "faster-whisper" | "whisperx"
    use_batched: bool           # 是否使用 BatchedInferencePipeline
    use_alignment: bool         # 是否使用 Wav2Vec2 對齊
    use_diarization: bool       # 是否使用說話者分離
    compute_type: str           # "int8" | "float16" | "float32"
    batch_size: int             # 批次大小
    chunk_length_s: float       # 分段長度

def select_strategy(
    language: str,
    device: str,
    enable_diarization: bool = False,
    enable_alignment: bool = False,
) -> TranscriptionStrategy:
    """根據需求選擇最佳策略"""
    
    # 英文且需要高效能 → distil
    if language in ("en", "auto") and not enable_diarization:
        return TranscriptionStrategy(
            model="distil-large-v3.5",
            engine="faster-whisper",
            use_batched=device == "cuda",
            use_alignment=False,
            use_diarization=False,
            compute_type="float16" if device == "cuda" else "int8",
            batch_size=16 if device == "cuda" else 1,
            chunk_length_s=30,
        )
    
    # 需要說話者分離 → whisperX
    if enable_diarization:
        return TranscriptionStrategy(
            model="large-v3",
            engine="whisperx",
            use_batched=True,
            use_alignment=language in ("en",),  # 僅英文支援對齊
            use_diarization=True,
            compute_type="float16",
            batch_size=16,
            chunk_length_s=30,
        )
    
    # 其他語言 → 標準 large-v3
    return TranscriptionStrategy(
        model="large-v3",
        engine="faster-whisper",
        use_batched=device == "cuda",
        use_alignment=False,
        use_diarization=False,
        compute_type="float16" if device == "cuda" else "int8",
        batch_size=16 if device == "cuda" else 1,
        chunk_length_s=30,
    )
```

**Step 2：統一轉錄介面**
```python
def transcribe_unified(audio_path: str, strategy: TranscriptionStrategy) -> dict:
    """統一轉錄介面"""
    if strategy.engine == "whisperx":
        return transcribe_with_whisperx(audio_path, strategy)
    else:
        return transcribe_with_faster_whisper(audio_path, strategy)
```

### D.4 預估工時

| 項目 | 工時 |
|------|------|
| 策略配置系統 | 2-3 小時 |
| faster-whisper 升級（方案 A） | 5.5-8.5 小時 |
| whisperX 整合（方案 C） | 7-12 小時 |
| 統一轉錄介面 | 2-3 小時 |
| API 端點更新 | 1-2 小時 |
| 測試驗證 | 3-4 小時 |
| **總計** | **20.5-32.5 小時** |

---

## 方案比較總表

### 功能比較

| 功能 | 方案 A | 方案 B | 方案 C | 方案 D |
|------|--------|--------|--------|--------|
| 多語言支援 | ✅ | ❌（僅英文） | ✅ | ✅ |
| 效能提升 | 2-4x | 6x（英文） | 1x（+20% 對齊） | 2-6x（動態） |
| 說話者分離 | ❌ | ❌ | ✅ | ✅（可選） |
| 精準字級時間戳 | ❌ | ❌ | ✅ | ✅（可選） |
| 實施難度 | 中 | 極低 | 中高 | 高 |
| 預估工時 | 5.5-8.5h | 0.5-5.5h | 7-15h | 20.5-32.5h |
| 維護成本 | 低 | 極低 | 中 | 中 |
| 風險 | 低 | 極低 | 中 | 中高 |

### 硬體需求比較

| 硬體 | 方案 A | 方案 B | 方案 C | 方案 D |
|------|--------|--------|--------|--------|
| 最小 GPU VRAM | 8GB | 6GB | 8GB | 8GB |
| 推薦 GPU VRAM | 16GB | 8GB | 16GB | 16GB |
| CPU 記憶體 | 4GB | 4GB | 8GB | 8GB |
| 儲存空間 | +0GB | +3GB | +10GB | +13GB |
| Docker 大小增加 | ~0MB | ~300MB | ~2GB | ~2.5GB |

### 適用場景推薦

| 場景 | 推薦方案 | 理由 |
|------|---------|------|
| **純英文轉錄，追求極致效能** | 方案 B | 6 倍加速，零程式碼改動 |
| **多語言，需要說話者分離** | 方案 C | whisperX 獨有功能 |
| **多語言，追求平衡** | 方案 A | 2-4x 加速，風險低 |
| **全場景最佳化** | 方案 D | 動態選擇最佳策略 |
| **預算有限，快速見效** | 方案 B（英文） | 0.5 小時實施 |
| **長期投資，功能完整** | 方案 D | 涵蓋所有場景 |

---

## 附錄：現有 faster-whisper 效能優化建議

在考慮任何升級方案之前，可以先優化現有配置：

### A.1 啟用 INT8 量化（GPU）

```bash
# .env
WHISPER_COMPUTE_TYPE=int8_float16  # GPU 混合量化
```

**效果：** VRAM 減少 50%，速度提升 10-20%

### A.2 調整 CPU 執行緒數

```bash
# .env
WHISPER_CPU_THREADS=8  # 增加執行緒數（不超過 CPU 核心數）
```

### A.3 使用較小模型

```python
# 根據音檔長度動態選擇模型
def get_recommended_model(duration_seconds):
    if duration_seconds < 120:
        return "tiny"      # 2 分鐘以內
    elif duration_seconds < 600:
        return "base"      # 10 分鐘以內
    elif duration_seconds < 1800:
        return "small"     # 30 分鐘以內
    else:
        return "medium"    # 30 分鐘以上
```

### A.4 優化 VAD 參數

```python
# 減少 VAD 過濾的嚴格度，提升速度
vad_parameters = {
    "min_silence_duration_ms": 500,  # 從 300 增加到 500
    "threshold": 0.5,                # 從 0.6 降低到 0.5
    "speech_pad_ms": 300             # 從 200 增加到 300
}
```

### A.5 模型預熱

```python
# 啟動時預載模型，避免首次請求延遲
@app.on_event("startup")
async def startup():
    # 預載常用模型
    get_model("base", device="cpu", compute_type="int8")
```
