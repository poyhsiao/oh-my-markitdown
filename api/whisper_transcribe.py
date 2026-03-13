"""
Whisper 轉錄模組
使用 Faster-Whisper 進行本地語音轉文字
"""

import os
import tempfile
import subprocess
from typing import Optional, Tuple
from faster_whisper import WhisperModel

# 從環境變數讀取配置
DEFAULT_MODEL = os.getenv("WHISPER_MODEL", "base")
DEFAULT_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
DEFAULT_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

# 全局模型快取（避免重複載入）
_model_cache = {}

def get_model(
    model_size: str = None, 
    device: str = None, 
    compute_type: str = None
):
    """
    獲取或載入 Whisper 模型
    
    Args:
        model_size: 模型大小 (tiny, base, small, medium, large)
        device: 運行設備 (cpu, cuda)
        compute_type: 計算類型 (int8, float16, float32)
    
    Returns:
        WhisperModel 實例
    """
    # 使用環境變數或默認值
    model_size = model_size or DEFAULT_MODEL
    device = device or DEFAULT_DEVICE
    compute_type = compute_type or DEFAULT_COMPUTE_TYPE
    
    cache_key = f"{model_size}_{device}_{compute_type}"
    
    if cache_key not in _model_cache:
        print(f"[Whisper] 載入模型: {model_size} (device={device}, compute_type={compute_type})")
        _model_cache[cache_key] = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )
    
    return _model_cache[cache_key]


def transcribe_audio(
    audio_path: str,
    language: str = "zh",
    model_size: str = "base",
    device: str = "cpu",
    compute_type: str = "int8",
    word_timestamps: bool = False
) -> Tuple[str, dict]:
    """
    轉錄音訊檔案
    
    Args:
        audio_path: 音訊檔案路徑
        language: 語言代碼 (zh, en, ja, ko 等)
        model_size: 模型大小
        device: 運行設備
        compute_type: 計算類型
        word_timestamps: 是否返回詞級時間戳
    
    Returns:
        (轉錄文字, 元數據)
    """
    # 載入模型
    model = get_model(model_size, device, compute_type)
    
    # 轉錄
    segments, info = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=word_timestamps,
        vad_filter=True,  # 使用 VAD 過濾靜音
        vad_parameters=dict(min_silence_duration_ms=500)
    )
    
    # 組合文字
    transcript_lines = []
    for segment in segments:
        transcript_lines.append(segment.text)
    
    transcript = " ".join(transcript_lines)
    
    # 元數據
    metadata = {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "duration_after_vad": info.duration_after_vad,
        "segments_count": len(list(segments)) if segments else 0,
        "model": model_size,
    }
    
    return transcript, metadata


def transcribe_with_timestamps(
    audio_path: str,
    language: str = "zh",
    model_size: str = "base"
) -> Tuple[str, list]:
    """
    轉錄音訊並返回時間戳
    
    Args:
        audio_path: 音訊檔案路徑
        language: 語言代碼
        model_size: 模型大小
    
    Returns:
        (轉錄文字, 段落列表)
    """
    model = get_model(model_size)
    
    segments, info = model.transcribe(
        audio_path,
        language=language,
        vad_filter=True
    )
    
    segments_list = []
    transcript_lines = []
    
    for segment in segments:
        segments_list.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text
        })
        transcript_lines.append(segment.text)
    
    return " ".join(transcript_lines), segments_list


def download_youtube_audio(url: str, output_dir: str = "/tmp") -> Tuple[str, str]:
    """
    下載 YouTube 影片的音訊
    
    Args:
        url: YouTube URL
        output_dir: 輸出目錄
    
    Returns:
        (音訊檔案路徑, 影片標題)
    """
    # 獲取影片資訊
    result = subprocess.run(
        ["yt-dlp", "--print", "%(title)s|||%(id)s", url],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    if result.returncode != 0:
        raise Exception(f"獲取 YouTube 資訊失敗: {result.stderr}")
    
    parts = result.stdout.strip().split("|||")
    title = parts[0] if len(parts) > 0 else "Unknown"
    video_id = parts[1] if len(parts) > 1 else "unknown"
    
    # 下載音訊
    output_path = os.path.join(output_dir, f"{video_id}.mp3")
    
    result = subprocess.run(
        ["yt-dlp", "-x", "--audio-format", "mp3", "-o", output_path, url],
        capture_output=True,
        text=True,
        timeout=300
    )
    
    if result.returncode != 0:
        raise Exception(f"下載 YouTube 音訊失敗: {result.stderr}")
    
    return output_path, title


def transcribe_youtube_video(
    url: str,
    language: str = "zh",
    model_size: str = "base",
    output_dir: str = "/tmp"
) -> dict:
    """
    下載 YouTube 影片並轉錄
    
    Args:
        url: YouTube URL
        language: 語言代碼
        model_size: 模型大小
        output_dir: 臨時檔案目錄
    
    Returns:
        包含轉錄結果和元數據的字典
    """
    # 下載音訊
    audio_path, title = download_youtube_audio(url, output_dir)
    
    try:
        # 轉錄
        transcript, metadata = transcribe_audio(
            audio_path,
            language=language,
            model_size=model_size
        )
        
        return {
            "success": True,
            "title": title,
            "transcript": transcript,
            "metadata": metadata,
            "audio_path": audio_path
        }
    
    except Exception as e:
        # 清理臨時檔案
        if os.path.exists(audio_path):
            os.unlink(audio_path)
        raise e


def format_transcript_as_markdown(
    title: str,
    transcript: str,
    metadata: dict,
    include_metadata: bool = True
) -> str:
    """
    將轉錄結果格式化為 Markdown
    
    Args:
        title: 影片標題
        transcript: 轉錄文字
        metadata: 元數據
        include_metadata: 是否包含元數據
    
    Returns:
        Markdown 格式的字串
    """
    md_lines = [f"# {title}", ""]
    
    if include_metadata:
        md_lines.extend([
            "## 轉錄資訊",
            "",
            f"- **語言**: {metadata.get('language', 'unknown')}",
            f"- **時長**: {metadata.get('duration', 0):.1f} 秒",
            f"- **模型**: {metadata.get('model', 'unknown')}",
            "",
            "---",
            ""
        ])
    
    md_lines.extend([
        "## 轉錄內容",
        "",
        transcript
    ])
    
    return "\n".join(md_lines)


# 支援的語言代碼
SUPPORTED_LANGUAGES = {
    "zh": "中文",
    "zh-TW": "繁體中文",
    "zh-CN": "簡體中文",
    "en": "英文",
    "ja": "日文",
    "ko": "韓文",
    "fr": "法文",
    "de": "德文",
    "es": "西班牙文",
    "pt": "葡萄牙文",
    "ru": "俄文",
    "ar": "阿拉伯文",
    "hi": "印地文",
    "th": "泰文",
    "vi": "越南文",
}