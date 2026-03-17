# YouTube 轉錄加速 - 任務清單

**日期**: 2026-03-17
**版本**: 1.0
**狀態**: 進行中

---

## 任務概覽

| ID | 任務 | 優先級 | 狀態 | 預估時間 |
|----|------|--------|------|----------|
| T-1 | 實作 `check_available_subtitles()` | 高 | ✅ 完成 | 30 分鐘 |
| T-2 | 實作 `download_and_convert_subtitles()` | 高 | ✅ 完成 | 45 分鐘 |
| T-3 | 修改 `transcribe_youtube_video()` | 高 | ✅ 完成 | 30 分鐘 |
| T-4 | 優化慢速路徑 | 中 | ✅ 完成 | 20 分鐘 |
| T-5 | 更新 API 端點參數 | 高 | ✅ 完成 | 15 分鐘 |
| T-6 | 更新回應格式 | 中 | ✅ 完成 | 15 分鐘 |
| T-7 | 新增單元測試 | 中 | ✅ 完成 | 45 分鐘 |
| T-8 | 更新文件 | 低 | ✅ 完成 | 20 分鐘 |

---

## T-1: 實作 `check_available_subtitles()` 函數

### 目標

檢查 YouTube 影片是否有可用的字幕（手動或自動）。

### 實作位置

`api/whisper_transcribe.py`

### 函數簽名

```python
def check_available_subtitles(url: str) -> dict:
    """
    檢查 YouTube 影片可用的字幕
    
    Args:
        url: YouTube URL
    
    Returns:
        {
            "has_manual": bool,      # 是否有手動上傳字幕
            "has_auto": bool,        # 是否有自動生成字幕  
            "available_langs": list, # 可用語言列表，如 ['zh-Hant', 'en']
            "recommended_lang": str   # 推薦使用的語言
        }
    """
```

### 實作細節

1. 使用 `yt-dlp --list-subs --no-download <url>` 命令
2. 解析輸出：
   - 找到 `Available subtitles` 行 → 手動字幕
   - 找到 `Automatic captions` 行 → 自動字幕
3. 提取語言代碼
4. 根據語言優先順序推薦

### 語言優先順序

```python
SUBTITLE_LANG_PRIORITY = ['zh-Hant', 'zh-Hans', 'zh-TW', 'zh-CN', 'en']
```

### 錯誤處理

- 網路錯誤：返回空結果
- 影片不存在：拋出異常
- 無字幕：`has_manual=False`, `has_auto=False`, `available_langs=[]`

### 驗收標準

- [x] 正確識別手動字幕
- [x] 正確識別自動字幕
- [x] 返回正確的語言列表
- [x] 推薦語言符合優先順序
- [x] 無字幕時返回正確的空結果

---

## T-2: 實作 `download_and_convert_subtitles()` 函數

### 目標

下載 YouTube 字幕並轉換為純文字格式。

### 實作位置

`api/whisper_transcribe.py`

### 函數簽名

```python
def download_and_convert_subtitles(
    url: str,
    output_dir: str = "/tmp",
    preferred_langs: list = None
) -> Tuple[str, dict]:
    """
    下載字幕並轉換為純文字
    
    Args:
        url: YouTube URL
        output_dir: 暫存目錄
        preferred_langs: 語言優先順序（預設使用 SUBTITLE_LANG_PRIORITY）
    
    Returns:
        (字幕純文字, metadata)
    """
```

### 實作細節

1. 使用 `yt-dlp` 下載字幕：
   ```bash
   yt-dlp --write-subs --write-auto-subs \
          --sub-lang <langs> \
          --skip-download \
          --sub-format vtt \
          -o <output_path> \
          <url>
   ```

2. 找到下載的 VTT 檔案

3. 解析 VTT：
   - 移除 `WEBVTT` header
   - 移除時間戳行（含 `-->`）
   - 移除純數字行
   - 合併文字行

4. 產生 metadata：
   ```python
   metadata = {
       "source": "youtube_subtitles",
       "language": "zh-Hant",  # 實際使用的語言
       "is_auto_generated": False,  # 是否為自動生成
   }
   ```

### 錯誤處理

- 下載失敗：拋出異常
- 無匹配語言：嘗試下一優先語言
- 所有語言都失敗：拋出異常

### 驗收標準

- [x] 成功下載字幕
- [x] VTT 正確轉換為純文字
- [x] metadata 正確
- [x] 暫存檔案正確清理

---

## T-3: 修改 `transcribe_youtube_video()` 加入快速路徑

### 目標

修改主函數，根據字幕可用性選擇快速或慢速路徑。

### 實作位置

`api/whisper_transcribe.py`

### 修改內容

```python
def transcribe_youtube_video(
    url: str,
    language: str = "zh",
    model_size: str = "base",
    output_dir: str = "/tmp",
    prefer_subtitles: bool = True  # 新增參數
) -> dict:
    # 快速路徑：優先使用字幕
    if prefer_subtitles:
        subtitle_info = check_available_subtitles(url)
        
        if subtitle_info["available_langs"]:
            # 有字幕，走快速路徑
            transcript, metadata = download_and_convert_subtitles(
                url, output_dir, [subtitle_info["recommended_lang"]]
            )
            return {
                "success": True,
                "title": get_video_title(url),
                "transcript": transcript,
                "metadata": metadata
            }
    
    # 慢速路徑：使用 Whisper
    audio_path, title = download_youtube_audio(url, output_dir)
    # ... 現有邏輯
```

### 驗收標準

- [x] 有字幕時走快速路徑
- [x] 無字幕時走慢速路徑
- [x] `prefer_subtitles=False` 時強制慢速路徑
- [x] 回應格式正確

---

## T-4: 優化慢速路徑

### 目標

優化 Whisper 轉錄速度。

### 實作位置

`api/whisper_transcribe.py`

### 優化項目

#### 4.1 低品質音訊下載

修改 `download_youtube_audio()`:

```python
# 新增參數
def download_youtube_audio(
    url: str, 
    output_dir: str = "/tmp",
    audio_quality: str = "128K"  # 新增：可選 "64K" 加速下載
) -> Tuple[str, str]:
    # 修改 yt-dlp 命令
    result = subprocess.run([
        "yt-dlp", 
        "--no-check-certificate",
        "-x", 
        "--audio-format", "mp3",
        "--audio-quality", audio_quality,  # 使用可變品質
        "-o", output_path, 
        url
    ], ...)
```

#### 4.2 多線程轉錄

修改 `transcribe_audio()`:

```python
def transcribe_audio(
    audio_path: str,
    language: str = "auto",
    model_size: str = "base",
    device: str = "cpu",
    compute_type: str = "int8",
    word_timestamps: bool = False,
    cpu_threads: int = 4  # 新增：CPU 線程數
) -> Tuple[str, dict]:
    model = get_model(model_size, device, compute_type)
    
    segments, info = model.transcribe(
        audio_path,
        language=actual_language,
        word_timestamps=word_timestamps,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        cpu_threads=cpu_threads  # 使用多線程
    )
```

### 驗收標準

- [x] 低品質音訊下載成功
- [x] 多線程轉錄成功
- [x] 整體速度提升 30%+

---

## T-5: 更新 API 端點參數

### 目標

更新 `/api/v1/convert/youtube` 端點參數。

### 實作位置

`api/main.py`

### 修改內容

```python
@api_router.post("/convert/youtube")
async def transcribe_youtube(
    release_slot = Depends(require_slot),
    url: str = Query(..., description="YouTube video URL"),
    language: str = Query("zh", description="Language code"),
    model_size: str = Query("base", description="Model size"),
    return_format: str = Query("markdown", description="Response format"),
    include_timestamps: bool = Query(False, description="Include timestamps"),
    include_metadata: bool = Query(True, description="Include metadata"),
    # 新增參數
    prefer_subtitles: bool = Query(True, description="Prefer YouTube subtitles if available"),
    fast_mode: bool = Query(False, description="Enable fast mode with optimizations")
):
```

### 驗收標準

- [x] 新參數可正確接收
- [x] 參數預設值正確
- [x] Swagger 文件更新

---

## T-6: 更新回應格式

### 目標

更新回應格式，新增處理來源資訊。

### 實作位置

`api/main.py`

### 回應格式

```python
# 成功回應
{
    "success": True,
    "title": "影片標題",
    "transcript": "轉錄文字...",
    "metadata": {
        "source": "youtube_subtitles",  # 或 "whisper"
        "language": "zh-Hant",
        "is_auto_generated": False,
        "duration": 1800,
        "model": "base",  # Whisper 時才有
        "processing_time_ms": 2500
    }
}
```

### 驗收標準

- [x] `source` 欄位正確
- [x] `language` 正確
- [x] `is_auto_generated` 正確
- [x] `processing_time_ms` 正確

---

## T-7: 新增單元測試

### 目標

新增測試覆蓋新功能。

### 實作位置

`tests/api/test_whisper.py`（新建）

### 測試案例

```python
class TestCheckAvailableSubtitles:
    """測試字幕檢查功能"""
    
    def test_has_manual_subtitles(self):
        """測試有手動字幕的影片"""
        
    def test_has_auto_subtitles(self):
        """測試有自動字幕的影片"""
        
    def test_no_subtitles(self):
        """測試無字幕的影片"""
        
    def test_language_priority(self):
        """測試語言優先順序"""

class TestDownloadAndConvertSubtitles:
    """測試字幕下載與轉換"""
    
    def test_download_vtt(self):
        """測試 VTT 下載"""
        
    def test_vtt_to_text_conversion(self):
        """測試 VTT 轉純文字"""
        
    def test_language_fallback(self):
        """測試語言降級"""

class TestTranscribeYouTubeVideo:
    """測試整合功能"""
    
    def test_fast_path_with_subtitles(self):
        """測試快速路徑"""
        
    def test_slow_path_without_subtitles(self):
        """測試慢速路徑"""
        
    def test_force_whisper(self):
        """測試強制使用 Whisper"""
```

### 驗收標準

- [x] 測試覆蓋率 > 80%
- [x] 所有測試通過

---

## T-8: 更新文件

### 目標

更新相關文件。

### 更新清單

| 文件 | 更新內容 |
|------|----------|
| `CHANGELOG.md` | 新增功能說明 |
| `docs/API_REFERENCE.md` | 更新端點參數說明 |
| `README.md` | 更新功能列表 |

### CHANGELOG 更新

```markdown
### Added
- YouTube 字幕優先策略，大幅加速有字幕影片的轉錄速度
- 新增 `prefer_subtitles` 參數控制是否優先使用字幕
- 新增 `fast_mode` 參數啟用快速模式
```

### 驗收標準

- [x] CHANGELOG 已更新
- [x] API_REFERENCE 已更新
- [x] README 已更新

---

## 任務依賴關係

```
T-1 (字幕檢查) ──┬──> T-3 (主流程修改) ──> T-5 (API 參數) ──> T-7 (測試)
                 │
T-2 (字幕下載) ─┘
                                            T-4 (優化) ──> T-6 (回應格式) ──> T-8 (文件)
```

**可並行任務**:
- T-1, T-2 可並行
- T-4 可與 T-3 並行
- T-7, T-8 可在最後並行

---

## 風險與緩解

| 風險 | 緩解措施 | 負責任務 |
|------|----------|----------|
| YouTube 字幕格式變化 | 解析邏輯要容錯 | T-2 |
| 多線程記憶體增加 | 可配置線程數 | T-4 |
| 測試環境無法連 YouTube | 使用 mock | T-7 |

---

## 完成定義

任務視為完成需滿足：

1. [x] 程式碼實作完成
2. [x] 單元測試通過
3. [x] LSP 檢查無錯誤（專案內相關）
4. [x] 文件已更新
5. [ ] 程式碼已 commit