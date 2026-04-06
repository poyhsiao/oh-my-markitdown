# insanely-fast-whisper 取代評估報告

> **Date:** 2026-04-05  
> **Author:** Kimhsiao  
> **Status:** 不建議採用

---

## 一、結論

**不建議以 insanely-fast-whisper 取代目前的 faster-whisper。**

三大主因：

1. **不是獨立 Python 庫** — 本質是 CLI 包裝器，底層為 Hugging Face Transformers pipeline，無法 `import insanely_fast_whisper`
2. **維護已停滯** — 最後更新 2024-05-27（近 2 年前），生產環境風險高
3. **缺少關鍵功能** — 無 VAD 過濾、無 INT8 量化、無 BatchedInferencePipeline、CPU 未優化

---

## 二、技術架構差異

| 項目 | 目前（faster-whisper） | insanely-fast-whisper |
|------|----------------------|----------------------|
| **底層引擎** | CTranslate2（C++ 推理引擎） | Hugging Face Transformers（PyTorch） |
| **導入方式** | `from faster_whisper import WhisperModel` | 無法 import，需直接用 `transformers.pipeline()` |
| **模型初始化** | `WhisperModel(size, device, compute_type)` | `pipeline("asr", model=..., torch_dtype=..., device=...)` |
| **輸出型別** | `Generator[Segment]` + `TranscriptionInfo` | `Dict: {"text": str, "chunks": [{"text": str, "timestamp": (start, end)}]}` |
| **量化支援** | INT8 / FP16 / FP32（執行時切換） | 僅 FP16（需手動配置） |
| **VAD 過濾** | ✅ 內建 Silero VAD（`vad_filter=True`） | ❌ 不支援，需自行實作 |
| **CPU 支援** | ✅ 完善（`cpu_threads` 參數） | ⚠️ 可行但未優化 |
| **Batched Pipeline** | ✅ `BatchedInferencePipeline` | ❌ 無 |
| **Flash Attention 2** | ❌ 不支援 | ✅ 支援（需額外安裝） |
| **GPU 效能** | 基準值 | 約快 5-6 倍（A100 + FA2） |
| **CPU 效能** | 已優化 | 無優化資料，可能更慢 |

### 程式碼對比

**目前（faster-whisper）：**
```python
from faster_whisper import WhisperModel

model = WhisperModel("large-v3", device="cuda", compute_type="float16")
segments, info = model.transcribe("audio.mp3", beam_size=5, language="en")

for segment in segments:
    print(f"[{segment.start} -> {segment.end}] {segment.text}")
```

**insanely-fast-whisper（Transformers Pipeline）：**
```python
from transformers import pipeline
import torch

pipe = pipeline(
    "automatic-speech-recognition",
    model="openai/whisper-large-v3",
    torch_dtype=torch.float16,
    device="cuda:0",
)

outputs = pipe("audio.mp3", chunk_length_s=30, batch_size=24, return_timestamps=True)
print(outputs["text"])
```

---

## 三、受影響範圍

### 3.1 需要改寫的檔案

| 檔案 | 影響程度 | 說明 |
|------|---------|------|
| `api/whisper_transcribe.py` | 🔴 **完全重寫** | 核心轉錄邏輯，所有 `WhisperModel` 呼叫需替換 |
| `api/chunking.py` | 🔴 **大幅修改** | `transcribe_chunk()` 直接依賴 faster-whisper API |
| `api/config.py` | 🟡 **中度修改** | `VALID_WHISPER_MODELS`、`WhisperConfig` 需調整 |
| `api/constants.py` | 🟡 **中度修改** | `COMPUTE_TYPE_BY_DEVICE` 不再適用 |
| `pyproject.toml` | 🟡 **修改依賴** | 移除 `faster-whisper`，新增 `transformers`、`accelerate`、`optimum` |
| `Dockerfile` | 🟡 **修改** | 預載模型指令需變更，可能需新增 Flash Attention 2 |
| `tests/` | 🟡 **修改** | 所有 whisper 相關測試需更新 |

### 3.2 不需要改寫的檔案

| 檔案 | 原因 |
|------|------|
| `api/main.py` | API 端點不直接依賴 whisper 庫，只呼叫 `whisper_transcribe` 模組函式 |
| `api/auto_convert.py` | 不直接依賴 whisper |
| `api/subtitles.py` | YouTube 字幕處理，與 whisper 無關 |
| `api/youtube_client.py` | yt-dlp SDK，與 whisper 無關 |
| `cli.py` | CLI 呼叫 API，不受影響 |

---

## 四、深度影響分析

### 4.1 VAD 功能喪失（🔴 重大）

目前 `transcribe_audio()` 預設啟用 VAD：

```python
segments, info = model.transcribe(
    audio_path,
    vad_filter=True,
    vad_parameters={
        "min_silence_duration_ms": 300,
        "threshold": 0.6,
        "speech_pad_ms": 200
    }
)
```

**Transformers pipeline 不支援 VAD。** 遷移後需：
- 自行整合 Silero VAD 作為前置處理
- 或移除 VAD 功能（長音檔中非語音段落也會被轉錄，產生無意義輸出）

### 4.2 Chunking 邏輯需重構（🔴 重大）

`api/chunking.py` 的 `transcribe_chunk()` 直接使用 faster-whisper API，輸出格式為 `Generator[Segment]`。

Transformers pipeline 輸出格式為 `{"text": str, "chunks": [...]}`，`merge_transcription_results()` 的合併邏輯需要完全重寫。

### 4.3 模型快取機制需調整（🟡 中度）

目前 `ModelCache` 快取 `WhisperModel` 實例。Transformers pipeline 也可快取，但初始化方式不同，且 `pipe()` 的參數（`chunk_length_s`、`batch_size`）會影響行為。

### 4.4 metadata 欄位變更（🟡 中度）

| 欄位 | faster-whisper | Transformers |
|------|---------------|-------------|
| `language` | ✅ `info.language` | ✅ `info.language` |
| `language_probability` | ✅ `info.language_probability` | ✅ |
| `duration` | ✅ `info.duration` | ✅ |
| `duration_after_vad` | ✅ `info.duration_after_vad` | ❌ 不存在 |

### 4.5 CPU 環境效能可能下降（🟡 中度）

本專案預設 `WHISPER_DEVICE=cpu`、`WHISPER_COMPUTE_TYPE=int8`。

insanely-fast-whisper 的效能優勢**完全來自 GPU + Flash Attention 2**。在 CPU 環境下：
- Transformers 推理速度通常**慢於** CTranslate2
- 沒有 INT8 量化支援
- 沒有針對 CPU 的執行緒優化

**對於沒有 GPU 的部署環境，遷移後效能可能反而變差。**

---

## 五、遷移工作量估算

| 工作項目 | 預估工時 | 風險 |
|----------|---------|------|
| 重寫 `whisper_transcribe.py` 核心邏輯 | 4-6 小時 | 高 |
| 重構 `chunking.py` 的 `transcribe_chunk()` | 3-4 小時 | 高 |
| 重寫 `merge_transcription_results()` | 2-3 小時 | 中 |
| 調整 `config.py` 和 `constants.py` | 1-2 小時 | 低 |
| 實作 VAD 替代方案（或移除） | 2-4 小時 | 高 |
| 更新 `pyproject.toml` 依賴 | 0.5 小時 | 低 |
| 更新 `Dockerfile` | 1-2 小時 | 中 |
| 更新測試 | 2-3 小時 | 中 |
| API 回應格式相容性處理 | 1-2 小時 | 中 |
| **總計** | **16-27 小時** | |

---

## 六、總結評分

| 評估維度 | 評分 | 說明 |
|---------|------|------|
| 技術可行性 | ⭐⭐⭐ | 可行但需大量改寫 |
| 效能提升（GPU） | ⭐⭐⭐⭐⭐ | Flash Attention 2 確實快很多 |
| 效能提升（CPU） | ⭐ | 可能反而更慢 |
| 維護風險 | ⭐ | 專案已停更近 2 年 |
| 功能完整性 | ⭐⭐ | 缺少 VAD、INT8、Batched Pipeline |
| 遷移成本 | ⭐⭐ | 16-27 小時，涉及 7+ 檔案 |
| API 相容性 | ⭐⭐⭐ | 需處理 metadata 欄位變更 |

---

## 七、替代建議

如果目標是**提升轉錄效能**，請參考以下文件：

- [方案比較總覽](./whisper-alternatives-comparison.md) — 所有 Whisper 替代方案的完整比較
- [升級方案詳細](./whisper-upgrade-plans.md) — 三種推薦升級方案的深度分析
