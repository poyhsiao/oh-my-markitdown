# Whisper 替代方案完整比較

> **Date:** 2026-04-05  
> **Author:** Kimhsiao  
> **Scope:** 所有 Whisper-based 轉錄方案的技術比較

---

## 一、方案總覽

| # | 方案 | 類型 | 底層引擎 | 多語言 | 本專案整合難度 |
|---|------|------|---------|--------|---------------|
| 1 | **faster-whisper**（目前） | Python 庫 | CTranslate2 | ✅ | 已整合 |
| 2 | **insanely-fast-whisper** | CLI 包裝 | Transformers + FA2 | ✅ | 🔴 高 |
| 3 | **distil-whisper + faster-whisper** | Python 庫 | CTranslate2 + 蒸餾模型 | ❌ 僅英文 | 🟢 極低 |
| 4 | **whisper.cpp** | C/C++ 庫 | GGML | ✅ | 🟡 中 |
| 5 | **MLX Whisper** | Swift/Python 庫 | MLX (Apple) | ✅ | 🟡 中 |
| 6 | **TensorRT-LLM Whisper** | Python 庫 | TensorRT (NVIDIA) | ✅ | 🔴 高 |
| 7 | **OpenAI Whisper API** | 雲端 API | OpenAI 伺服器 | ✅ | 🟢 低 |
| 8 | **whisperX** | Python 庫 | faster-whisper + 擴展 | ✅ | 🟡 中 |

---

## 二、各方案詳細分析

### 2.1 faster-whisper（目前使用）

| 項目 | 說明 |
|------|------|
| **GitHub** | [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) |
| **Stars** | ~22K |
| **License** | MIT |
| **底層** | CTranslate2（C++ 推理引擎） |
| **語言** | Python |
| **多語言** | ✅ 99+ 語言 |
| **VAD** | ✅ 內建 Silero VAD |
| **量化** | ✅ INT8 / FP16 / FP32 |
| **Batched Pipeline** | ✅ `BatchedInferencePipeline` |
| **CPU 支援** | ✅ 完善（`cpu_threads` 參數） |
| **GPU 支援** | ✅ CUDA |
| **Apple Silicon** | ✅ MPS |
| **模型支援** | tiny / base / small / medium / large / distil-* |
| **Word Timestamps** | ✅ |
| **Streaming** | ❌ |
| **維護狀態** | ✅ 活躍 |

**優勢：**
- 本專案已完整整合
- CPU/GPU 雙支援，量化選項完整
- VAD 內建，chunking 機制完善
- 維護活躍，社群穩定

**劣勢：**
- GPU 效能不如 Flash Attention 2 優化方案
- 不支援串流轉錄

---

### 2.2 insanely-fast-whisper

| 項目 | 說明 |
|------|------|
| **GitHub** | [Vaibhavs10/insanely-fast-whisper](https://github.com/Vaibhavs10/insanely-fast-whisper) |
| **Stars** | ~12.3K |
| **License** | MIT |
| **底層** | Hugging Face Transformers + Flash Attention 2 |
| **語言** | Python（CLI 為主） |
| **多語言** | ✅ 取決於模型 |
| **VAD** | ❌ 不支援 |
| **量化** | ⚠️ 需手動配置 |
| **Batched Pipeline** | ❌ 無 |
| **CPU 支援** | ⚠️ 可行但未優化 |
| **GPU 支援** | ✅ CUDA + Flash Attention 2 |
| **Apple Silicon** | ✅ MPS（記憶體消耗高） |
| **模型支援** | 任何 Hugging Face Whisper 模型 |
| **Word Timestamps** | ✅ `return_timestamps="word"` |
| **Streaming** | ❌ |
| **維護狀態** | 🔴 停滯（最後更新 2024-05-27） |

**優勢：**
- GPU + Flash Attention 2 效能出色（A100 上比 faster-whisper 快 5-6 倍）
- 模型彈性大，可使用任何 Hugging Face checkpoint

**劣勢：**
- **不是 Python 庫**，無法 import，只是 CLI 包裝
- 維護停滯近 2 年
- 缺少 VAD、量化、Batched Pipeline
- CPU 效能未優化，可能比 faster-whisper 更慢
- Flash Attention 2 安裝複雜

> **詳細評估：** 請見 [insanely-fast-whisper-evaluation.md](./insanely-fast-whisper-evaluation.md)

---

### 2.3 distil-whisper + faster-whisper

| 項目 | 說明 |
|------|------|
| **GitHub** | [huggingface/distil-whisper](https://github.com/huggingface/distil-whisper) |
| **Stars** | ~3K |
| **License** | Apache 2.0 |
| **底層** | 知識蒸餾 + CTranslate2（透過 faster-whisper） |
| **語言** | Python |
| **多語言** | ❌ **僅英文** |
| **VAD** | ✅ 透過 faster-whisper |
| **量化** | ✅ 透過 faster-whisper |
| **Batched Pipeline** | ✅ 透過 faster-whisper |
| **CPU 支援** | ✅ 透過 faster-whisper |
| **GPU 支援** | ✅ CUDA |
| **Apple Silicon** | ✅ MPS |
| **模型支援** | distil-large-v3 / distil-large-v3.5 / distil-medium.en / distil-small.en |
| **Word Timestamps** | ✅ |
| **Streaming** | ❌ |
| **維護狀態** | ✅ 活躍（2025-03 更新） |

**可用模型：**

| 模型 | 參數量 | 速度（vs large-v3） | 短句 WER | 長句 WER | VRAM (FP16) |
|------|--------|---------------------|----------|----------|-------------|
| distil-large-v3 | 756M | **6.3x faster** | 9.7% | 10.8% | ~6GB |
| distil-large-v3.5 | 756M | 1.46x (vs turbo) | **7.08%** | 11.39% | ~6GB |
| distil-medium.en | 394M | 6.8x faster | 11.1% | 12.4% | ~3GB |
| distil-small.en | 166M | 5.6x faster | 12.1% | 12.8% | ~1.5GB |

**整合方式（零程式碼改動）：**
```python
# 只需更改模型名稱，其他程式碼完全不用動
model = WhisperModel("distil-large-v3", device="cuda", compute_type="float16")
# 或 CTranslate2 格式（更快）
model = WhisperModel("distil-whisper/distil-large-v3.5-ct2", device="cuda", compute_type="float16")
```

**優勢：**
- **零程式碼改動**，只需改模型名稱
- 速度提升 6 倍，準確率損失 <1% WER
- 完整保留 VAD、量化、chunking 功能
- 維護活躍（2025-03 更新）

**劣勢：**
- **僅支援英文**（本專案需要中文、日文、韓文等多語言）
- 如需多語言，必須 fallback 到原始 Whisper 模型

---

### 2.4 whisper.cpp

| 項目 | 說明 |
|------|------|
| **GitHub** | [ggml-org/whisper.cpp](https://github.com/ggml-org/whisper.cpp) |
| **Stars** | ~48K |
| **License** | MIT |
| **底層** | GGML（C/C++ 推理引擎） |
| **語言** | C/C++，Python bindings: `whisper-cpp-py` / `stt` |
| **多語言** | ✅ 99+ 語言 |
| **VAD** | ❌ 需自行整合 |
| **量化** | ✅ Q4_0 / Q5_0 / Q5_1 / Q8_0 / FP16 / FP32 |
| **CPU 支援** | ✅ 極佳（AVX / NEON 優化） |
| **GPU 支援** | ✅ CUDA / Metal |
| **Apple Silicon** | ✅ 原生 Metal 支援 |
| **模型支援** | 所有 Whisper 模型（含 GGML 格式） |
| **Word Timestamps** | ✅ |
| **Streaming** | ✅ 支援 |
| **維護狀態** | ✅ 極活躍（48K stars） |

**效能特徵：**
- CPU 模式：在某些報告中比 faster-whisper 更快（AVX 優化）
- 但也有報告指出 CPU 模式可能比 Python 版更慢（取決於硬體）
- 記憶體佔用極低（量化後可低至 ~100MB for base model）
- 無依賴，單一 binary 即可執行

**Python 整合範例：**
```python
from whisper_cpp import Whisper
# 或
import whispercpp as whisper
w = whisper.Whisper.from_pretrained("base")
result = w.transcribe("audio.wav")
```

**整合難度：🟡 中**
- 需要編譯 C++ 依賴或使用預編譯 wheel
- Python API 與 faster-whisper 不同，需改寫 `whisper_transcribe.py`
- chunking 邏輯需調整

**優勢：**
- 極低記憶體佔用
- 無外部依賴（不需要 PyTorch）
- 支援串流
- Apple Silicon 原生 Metal 支援

**劣勢：**
- Python API 成熟度不如 faster-whisper
- 無內建 VAD
- chunking 需自行實作
- CPU 效能表現不一致（有報告顯示比 Python 版慢）

---

### 2.5 MLX Whisper

| 項目 | 說明 |
|------|------|
| **GitHub** | [ml-explore/mlx-examples/whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) |
| **Stars** | mlx-examples ~10K |
| **License** | MIT |
| **底層** | MLX（Apple Silicon 專屬 ML 框架） |
| **語言** | Python + Swift |
| **多語言** | ✅ 99+ 語言 |
| **VAD** | ❌ 需自行整合 |
| **量化** | ✅ 4-bit / 8-bit |
| **CPU 支援** | ❌ 僅 Apple Silicon |
| **GPU 支援** | ❌ 僅 Apple Silicon GPU |
| **Apple Silicon** | ✅ **原生優化**（M1/M2/M3/M4） |
| **模型支援** | 所有 Whisper 模型 |
| **Word Timestamps** | ✅ |
| **Streaming** | ✅ |
| **維護狀態** | ✅ 活躍（Apple 官方維護） |

**Apple Silicon 效能（M4 Mac Mini 基準）：**

| 模型 | 處理時間（10 分鐘音頻） | Real-Time Factor |
|------|------------------------|-----------------|
| tiny | ~15 秒 | ~40x |
| base | ~25 秒 | ~24x |
| small | ~45 秒 | ~13x |
| medium | ~90 秒 | ~6.7x |
| large-v3 | ~150 秒 | ~4x |

**整合難度：🟡 中**
- 僅限 Apple Silicon 硬體
- 需要 `mlx` 和 `mlx-whisper` 套件
- API 與 faster-whisper 不同

**優勢：**
- Apple Silicon 上效能最佳
- Apple 官方維護
- 記憶體效率優異

**劣勢：**
- **僅限 Apple Silicon**（無法在 Linux/Windows 或 Intel Mac 上執行）
- 無法用於 Docker 部署（除非使用 Apple Silicon 容器）
- 本專案預設部署在 Docker/Linux 環境

---

### 2.6 TensorRT-LLM Whisper

| 項目 | 說明 |
|------|------|
| **GitHub** | [NVIDIA/TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM) |
| **Stars** | ~21K |
| **License** | Apache 2.0 |
| **底層** | TensorRT + TensorRT-LLM |
| **語言** | Python + C++ |
| **多語言** | ✅ |
| **VAD** | ❌ 需自行整合 |
| **量化** | ✅ FP8 / INT8 / INT4 |
| **CPU 支援** | ❌ 僅 NVIDIA GPU |
| **GPU 支援** | ✅ **NVIDIA GPU 專屬優化** |
| **Apple Silicon** | ❌ 不支援 |
| **模型支援** | Whisper large-v3 等 |
| **Word Timestamps** | ✅ |
| **Streaming** | ✅ |
| **維護狀態** | ✅ 活躍（NVIDIA 官方） |

**效能：**
- NVIDIA GPU 上理論最快方案
- 支援 FP8 量化（Ampere+ 架構）
- 需要模型編譯步驟（build engine）

**整合難度：🔴 高**
- 僅支援 NVIDIA GPU（CUDA 8.0+）
- 需要預先編譯 TensorRT engine（耗時）
- 設定複雜，需要 CUDA Toolkit + TensorRT
- 與本專案目前架構差異大

**優勢：**
- NVIDIA GPU 上效能極致
- FP8 量化支援（最新 GPU）
- 高吞吐量

**劣勢：**
- 設定極度複雜
- 僅限 NVIDIA GPU
- 需要模型編譯步驟
- 不適合本專案的 Docker 輕量部署

---

### 2.7 OpenAI Whisper API

| 項目 | 說明 |
|------|------|
| **提供者** | OpenAI |
| **類型** | 雲端 API |
| **多語言** | ✅ 99+ 語言 |
| **定價** | **$0.006/分鐘**（約 $0.36/小時） |
| **VAD** | ✅ 伺服器端處理 |
| **量化** | N/A（伺服器端） |
| **硬體需求** | ❌ 無（雲端） |
| **模型支援** | whisper-1（等同 large-v2） |
| **Word Timestamps** | ❌ 不支援 |
| **Streaming** | ❌ |
| **維護狀態** | ✅ OpenAI 維護 |

**成本估算：**

| 月處理量 | 月費用 |
|---------|--------|
| 10 小時 | $3.60 |
| 100 小時 | $36.00 |
| 1,000 小時 | $360.00 |
| 10,000 小時 | $3,600.00 |

**整合難度：🟢 低**
```python
from openai import OpenAI

client = OpenAI()
with open("audio.mp3", "rb") as f:
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=f,
        language="zh"
    )
```

**優勢：**
- 零硬體需求
- 整合最簡單
- 準確率高（large-v2 等級）
- 無需維護模型

**劣勢：**
- **持續成本**（大量使用時費用可觀）
- **需要網路連線**
- **隱私疑慮**（音頻上傳至 OpenAI 伺服器）
- **速率限制**（OpenAI API 限流）
- 不支援 word timestamps

---

### 2.8 whisperX

| 項目 | 說明 |
|------|------|
| **GitHub** | [m-bain/whisperX](https://github.com/m-bain/whisperX) |
| **Stars** | ~21K |
| **License** | BSD-2 |
| **底層** | faster-whisper + 擴展 |
| **語言** | Python |
| **多語言** | ✅ |
| **VAD** | ✅ 內建 |
| **量化** | ✅ 透過 faster-whisper |
| **CPU 支援** | ✅ 透過 faster-whisper |
| **GPU 支援** | ✅ CUDA |
| **Apple Silicon** | ⚠️ 有限 |
| **模型支援** | faster-whisper 支援的所有模型 |
| **Word Timestamps** | ✅ **Wav2Vec2 對齊（更精準）** |
| **Speaker Diarization** | ✅ 說話者分離 |
| **維護狀態** | ✅ 活躍 |

**特色功能：**
- **Wav2Vec2 字級對齊**：比原生 whisper word timestamps 更精準
- **說話者分離**：自動識別不同說話者
- 基於 faster-whisper，可相容使用 distil 模型

**整合難度：🟡 中**
- 基於 faster-whisper，核心 API 相似
- 額外依賴：Wav2Vec2 模型、pyannote-audio（說話者分離）
- 需要更多 VRAM（Wav2Vec2 對齊模型）

**優勢：**
- 基於 faster-whisper，遷移成本低
- 字級對齊更精準
- 說話者分離功能
- 可搭配 distil 模型使用

**劣勢：**
- 額外依賴增加 Docker 大小
- Wav2Vec2 對齊僅支援部分語言（英文最佳）
- 說話者分離需要 pyannote-audio token

---

## 三、硬體需求比較

### 3.1 GPU VRAM 需求（FP16）

| 方案 | tiny | base | small | medium | large-v3 | distil-large-v3 |
|------|------|------|-------|--------|----------|----------------|
| faster-whisper | ~1GB | ~1GB | ~2GB | ~5GB | ~10GB | ~6GB |
| insanely-fast-whisper | ~1GB | ~1GB | ~2GB | ~5GB | ~10GB | ~6GB |
| whisper.cpp (Q8) | ~0.5GB | ~0.5GB | ~1GB | ~2.5GB | ~5GB | ~3GB |
| MLX Whisper (4-bit) | ~0.3GB | ~0.3GB | ~0.5GB | ~1.2GB | ~2.5GB | ~1.5GB |
| TensorRT-LLM (FP8) | ~0.5GB | ~0.5GB | ~1GB | ~2.5GB | ~5GB | ~3GB |

### 3.2 CPU 記憶體需求

| 方案 | base | small | medium | large-v3 |
|------|------|-------|--------|----------|
| faster-whisper (INT8) | ~0.7GB | ~1.4GB | ~3.5GB | ~7GB |
| insanely-fast-whisper | ~1GB | ~2GB | ~5GB | ~10GB |
| whisper.cpp (Q5_0) | ~0.4GB | ~0.8GB | ~2GB | ~4GB |

### 3.3 硬體平台相容性

| 方案 | x86 CPU | ARM CPU | NVIDIA GPU | Apple Silicon | Intel GPU |
|------|---------|---------|------------|--------------|-----------|
| faster-whisper | ✅ | ✅ | ✅ | ✅ (MPS) | ❌ |
| insanely-fast-whisper | ✅ | ✅ | ✅ | ✅ (MPS) | ❌ |
| distil-whisper | ✅ | ✅ | ✅ | ✅ (MPS) | ❌ |
| whisper.cpp | ✅ | ✅ | ✅ | ✅ (Metal) | ❌ |
| MLX Whisper | ❌ | ❌ | ❌ | ✅ | ❌ |
| TensorRT-LLM | ❌ | ❌ | ✅ | ❌ | ❌ |
| OpenAI API | ✅ | ✅ | ✅ | ✅ | ✅ |
| whisperX | ✅ | ✅ | ✅ | ⚠️ | ❌ |

---

## 四、效能比較矩陣

### 4.1 GPU 效能（相對速度，基準 = faster-whisper large-v3）

| 方案 | 相對速度 | 測試環境 |
|------|---------|---------|
| faster-whisper (large-v3, FP16) | 1.0x | A100 80GB |
| faster-whisper (large-v3, INT8) | 1.2x | A100 80GB |
| insanely-fast-whisper (FA2) | **5-6x** | A100 80GB |
| distil-large-v3 | **6.3x** | A100 80GB |
| distil-large-v3.5 | ~7x | A100 80GB |
| whisper.cpp (large-v3, FP16) | ~0.8x | A100 80GB |
| TensorRT-LLM (FP8) | **8-10x** | A100 80GB |
| MLX Whisper (large-v3) | ~2x | M3 Max |
| whisperX (large-v3) | 1.0x | A100 80GB |

### 4.2 CPU 效能（相對速度，基準 = faster-whisper base, INT8）

| 方案 | 相對速度 |
|------|---------|
| faster-whisper (base, INT8) | 1.0x |
| insanely-fast-whisper (base) | ~0.6x（更慢） |
| whisper.cpp (base, Q5_0) | ~1.2x |
| distil-small.en (INT8) | ~3x（但僅英文） |

### 4.3 多語言支援度

| 方案 | 中文 | 日文 | 韓文 | 泰文 | 越南文 | 總語言數 |
|------|------|------|------|------|--------|---------|
| faster-whisper | ✅ | ✅ | ✅ | ✅ | ✅ | 99+ |
| insanely-fast-whisper | ✅ | ✅ | ✅ | ✅ | ✅ | 99+ |
| distil-whisper | ❌ | ❌ | ❌ | ❌ | ❌ | **僅英文** |
| whisper.cpp | ✅ | ✅ | ✅ | ✅ | ✅ | 99+ |
| MLX Whisper | ✅ | ✅ | ✅ | ✅ | ✅ | 99+ |
| TensorRT-LLM | ✅ | ✅ | ✅ | ✅ | ✅ | 99+ |
| OpenAI API | ✅ | ✅ | ✅ | ✅ | ✅ | 99+ |
| whisperX | ✅ | ✅ | ✅ | ✅ | ✅ | 99+ |

---

## 五、本專案適用性評估

### 5.1 關鍵需求對照

本專案的核心需求：
1. **多語言支援**（中文、日文、韓文、泰文、越南文）
2. **Docker 部署**（Linux x86/ARM）
3. **CPU 部署為預設**（GPU 為可選）
4. **VAD 過濾**（減少無意義轉錄）
5. **長音檔 chunking**（避免 timeout）
6. **低維護成本**

| 方案 | 多語言 | Docker | CPU 預設 | VAD | Chunking | 維護成本 | 綜合評分 |
|------|--------|--------|---------|-----|----------|---------|---------|
| faster-whisper（目前） | ✅ | ✅ | ✅ | ✅ | ✅ | 低 | ⭐⭐⭐⭐⭐ |
| insanely-fast-whisper | ✅ | ⚠️ | ❌ | ❌ | ❌ | 高 | ⭐⭐ |
| distil-whisper | ❌ | ✅ | ✅ | ✅ | ✅ | 低 | ⭐⭐⭐（英文場景） |
| whisper.cpp | ✅ | ✅ | ✅ | ❌ | ❌ | 中 | ⭐⭐⭐ |
| MLX Whisper | ✅ | ❌ | ❌ | ❌ | ❌ | 中 | ⭐⭐ |
| TensorRT-LLM | ✅ | ⚠️ | ❌ | ❌ | ❌ | 高 | ⭐⭐ |
| OpenAI API | ✅ | N/A | N/A | ✅ | N/A | 低（但需付費） | ⭐⭐⭐ |
| whisperX | ✅ | ✅ | ✅ | ✅ | ✅ | 中 | ⭐⭐⭐⭐ |

### 5.2 推薦排序

| 排名 | 方案 | 適用場景 | 理由 |
|------|------|---------|------|
| 🥇 | **faster-whisper（維持現狀）** | 所有場景 | 已完整整合，功能完整，維護活躍 |
| 🥈 | **whisperX** | 需要說話者分離 | 基於 faster-whisper，額外提供字級對齊和說話者分離 |
| 🥉 | **whisper.cpp** | 嵌入式/低資源 | 極低記憶體佔用，無 PyTorch 依賴 |
| 4 | **distil-whisper** | **純英文場景** | 6 倍加速，零程式碼改動，但僅支援英文 |
| 5 | **OpenAI API** | 低用量/無 GPU | 零硬體需求，但持續成本 |
| 6 | **MLX Whisper** | Apple Silicon 專用 | Apple 晶片上效能最佳，但不支援 Docker/Linux |
| 7 | **TensorRT-LLM** | 高吞吐量 NVIDIA | NVIDIA GPU 上效能極致，但設定複雜 |
| 8 | **insanely-fast-whisper** | 不推薦 | 維護停滯，功能不足，遷移成本高 |
