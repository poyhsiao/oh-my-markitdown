# YouTube 轉錄加速設計

**日期**: 2026-03-17
**狀態**: 設計完成
**作者**: Kimhsiao

---

## 問題描述

YouTube 影片轉錄速度太慢，30-60 分鐘的影片需要等待較長時間。

**現有流程**:
```
YouTube URL → 下載音訊 (慢) → Whisper 轉錄 (慢) → 輸出
```

**瓶頸分析**:
1. 音訊下載：長影片需要數分鐘
2. Whisper 轉錄：CPU 環境下，30 分鐘影片約需 5-10 分鐘

---

## 解決方案：混合策略

### 整體流程

```
YouTube URL 進來
    ↓
[步驟 1] 取得影片資訊 + 檢查可用字幕
    ↓
有字幕？
├── YES → [快速路徑] 下載字幕 → 格式化輸出 (秒級)
└── NO  → [慢速路徑] 下載音訊 → Whisper 轉錄 → 格式化輸出 (分鐘級)
```

### 預期效果

| 場景 | 原速度 | 新速度 | 加速幅度 |
|------|--------|--------|----------|
| 有字幕的影片 | 5-10 分鐘 | 2-5 秒 | 99%+ |
| 無字幕的影片 | 5-10 分鐘 | 3-7 分鐘 | 30-40% |

---

## 詳細設計

### 一、字幕檢查邏輯

**函數簽名**:
```python
def check_available_subtitles(url: str) -> dict:
    """
    檢查 YouTube 影片可用的字幕
    
    Returns:
        {
            "has_manual": bool,      # 是否有手動上傳字幕
            "has_auto": bool,        # 是否有自動生成字幕  
            "available_langs": list, # 可用語言列表
            "recommended_lang": str   # 推薦使用的語言
        }
    """
```

**語言優先順序**:
1. 手動字幕 > 自動字幕（準確度較高）
2. 語言順序：`zh-Hant` > `zh-Hans` > `zh-TW` > `zh-CN` > `en`

**實作方式**:
```bash
# 使用 yt-dlp 列出可用字幕
yt-dlp --list-subs --no-download <url>
```

### 二、快速路徑（字幕下載）

**函數簽名**:
```python
def download_and_convert_subtitles(
    url: str,
    output_path: str,
    preferred_langs: list = ['zh-Hant', 'zh-Hans', 'en']
) -> tuple[str, dict]:
    """
    下載字幕並轉換為純文字
    
    Returns:
        (字幕純文字, metadata)
    """
```

**處理流程**:
1. 使用 `yt-dlp --write-subs --write-auto-subs` 下載字幕
2. 選擇 VTT 格式
3. 解析 VTT：移除 header、時間戳、序號
4. 合併文字行

**Metadata 欄位**:
- `source`: `"youtube_subtitles"`
- `language`: 實際語言
- `is_auto_generated`: bool

### 三、慢速路徑（Whisper 轉錄優化）

**優化項目**:

| 優化 | 做法 | 效果 |
|------|------|------|
| 降低音訊品質 | 下載 64kbps | 下載快 50% |
| 多線程 | `cpu_threads=8` (fast_mode) | CPU 多核並行 |
| VAD 優化 | `min_silence_duration_ms=500` | 跳過靜音 |

**預設保持**:
- 模型：`base`（平衡速度與準確度）
- 可讓使用者選擇 `tiny` 加速

---

## API 變更

### 端點：`/api/v1/convert/youtube`

**新增參數**:

| 參數 | 類型 | 預設值 | 說明 |
|------|------|--------|------|
| `prefer_subtitles` | bool | `true` | 優先使用 YouTube 字幕 |
| `model_size` | str | `base` | Whisper 模型大小 |
| `fast_mode` | bool | `false` | 啟用快速模式 |

**回應新增欄位**:

```json
{
  "success": true,
  "title": "影片標題",
  "transcript": "轉錄文字...",
  "metadata": {
    "source": "youtube_subtitles",
    "language": "zh-Hant",
    "is_auto_generated": false,
    "duration": 1800,
    "processing_time_ms": 2500
  }
}
```

**`source` 欄位值**:
- `"youtube_subtitles"`: 來自 YouTube 字幕（快速路徑）
- `"whisper"`: 來自 Whisper 轉錄（慢速路徑）

---

## 檔案變更清單

| 檔案 | 變更類型 | 說明 |
|------|----------|------|
| `api/whisper_transcribe.py` | 修改 | 新增字幕函數，修改主流程 |
| `api/main.py` | 修改 | 更新端點參數與回應 |
| `api/constants.py` | 修改 | 新增字幕語言常數 |

---

## 實作任務

- [ ] T-1: 實作 `check_available_subtitles()` 函數
- [ ] T-2: 實作 `download_and_convert_subtitles()` 函數
- [ ] T-3: 修改 `transcribe_youtube_video()` 加入快速路徑
- [ ] T-4: 優化慢速路徑（低品質音訊 + 多線程）
- [ ] T-5: 更新 API 端點參數
- [ ] T-6: 更新回應格式
- [ ] T-7: 新增單元測試
- [ ] T-8: 更新文件（CHANGELOG、API_REFERENCE）

---

## 測試計畫

1. **有字幕影片**：驗證快速路徑觸發，秒級完成
2. **無字幕影片**：驗證降級到 Whisper，速度合理
3. **`prefer_subtitles=false`**：強制使用 Whisper
4. **`fast_mode=true`**：驗證優化效果
5. **多語言字幕**：驗證語言優先順序

---

## 風險與緩解

| 風險 | 緩解措施 |
|------|----------|
| YouTube 字幕品質不一 | 提供參數讓使用者強制使用 Whisper |
| 部分影片無字幕 | 降級到 Whisper，保持可用性 |
| 多線程記憶體增加 | 可配置，預設保持合理值 |

---

## 後續優化（可選）

- 快取已處理影片的結果
- 支援更多字幕格式（SRT、TTML）
- 提供「字幕品質評分」讓使用者判斷