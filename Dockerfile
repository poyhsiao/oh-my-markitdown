FROM python:3.12-slim

LABEL maintainer="Kimhsiao <white.shopping@gmail.com>"
LABEL description="MarkItDown Docker with API - Convert files to Markdown via HTTP API with multi-language OCR"

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴
# 參考：https://github.com/microsoft/markitdown + 額外工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 基礎工具
    curl \
    ca-certificates \
    \
    # PDF 處理（pdfminer.six, pdfplumber）
    poppler-utils \
    \
    # 圖片處理（EXIF, OCR）
    libmagic1 \
    exiftool \
    libexif-dev \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra \
    tesseract-ocr-eng \
    tesseract-ocr-jpn \
    tesseract-ocr-kor \
    tesseract-ocr-tha \
    tesseract-ocr-vie \
    \
    # 音頻處理（pydub, SpeechRecognition）
    ffmpeg \
    \
    # 字體支持（OCR 和圖片處理）
    fonts-dejavu-core \
    fonts-liberation \
    fonts-noto-cjk \
    \
    # Office 文件處理（olefile, mammoth）
    libxml2-dev \
    libxslt1-dev \
    \
    # Python 依賴構建工具
    build-essential \
    \
    # 清理
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 安裝 uv（Python 套件管理器）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 複製依賴定義文件
COPY pyproject.toml uv.lock* README.md ./

# 使用 uv 安裝 Python 依賴
RUN uv sync --frozen --no-dev

# Pre-download Whisper base model (per spec Section 2.3)
# This ensures the model is available on first run without download delay
RUN uv run python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

# 創建目錄結構
RUN mkdir -p /app/input /app/output /app/data /app/api

# 複製 API 服務代碼
COPY api/__init__.py /app/api/__init__.py
COPY api/main.py /app/api/main.py
COPY api/config.py /app/api/config.py
COPY api/device_utils.py /app/api/device_utils.py
COPY api/whisper_transcribe.py /app/api/whisper_transcribe.py
COPY api/constants.py /app/api/constants.py
COPY api/middleware.py /app/api/middleware.py
COPY api/system.py /app/api/system.py
COPY api/response.py /app/api/response.py
COPY api/concurrency.py /app/api/concurrency.py
COPY api/subtitles.py /app/api/subtitles.py
COPY api/ip_whitelist.py /app/api/ip_whitelist.py
COPY api/youtube_grabber.py /app/api/youtube_grabber.py
COPY api/youtube_client.py /app/api/youtube_client.py
COPY api/audio_extractor.py /app/api/audio_extractor.py
COPY api/ocr_client.py /app/api/ocr_client.py

# 複製自動轉換腳本
COPY api/auto_convert.py /app/api/auto_convert.py

# 複製 CLI 工具
COPY cli.py /app/cli.py

# 複製腳本目錄
COPY scripts /app/scripts

# 複製測試目錄
COPY tests /app/tests

# 設置執行權限
RUN chmod +x /app/cli.py

# 暴露 API 端口
EXPOSE 8000

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 預設啟動 API 服務 (使用 uv run 執行虛擬環境中的命令)
CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
