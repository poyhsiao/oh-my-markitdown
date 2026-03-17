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
    # YouTube 下載工具
    yt-dlp \
    \
    # 清理
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 安裝 Python 依賴
# 參考官方 pyproject.toml 的 all 依賴組
RUN pip install --no-cache-dir \
    # MarkItDown 與所有可選依賴
    'markitdown[all]' \
    \
    # OCR 插件
    markitdown-ocr \
    \
    # FastAPI 和相關依賴
    fastapi \
    uvicorn \
    python-multipart \
    aiofiles \
    \
    # OpenAI（可選，用於高品質 OCR）
    openai \
    \
    # Azure Document Intelligence（可選）
    azure-ai-documentintelligence \
    azure-identity \
    \
    # Faster-Whisper（本地 STT，比 Whisper 快 2-4 倍）
    faster-whisper \
    psutil \
    \
    # Testing dependencies
    pytest \
    pytest-asyncio

# Pre-download Whisper base model (per spec Section 2.3)
# This ensures the model is available on first run without download delay
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

# 創建目錄結構
RUN mkdir -p /app/input /app/output /app/data /app/api

# 複製 API 服務代碼
COPY api/__init__.py /app/api/__init__.py
COPY api/main.py /app/api/main.py
COPY api/config.py /app/api/config.py
COPY api/whisper_transcribe.py /app/api/whisper_transcribe.py
COPY api/constants.py /app/api/constants.py
COPY api/middleware.py /app/api/middleware.py
COPY api/system.py /app/api/system.py
COPY api/response.py /app/api/response.py
COPY api/concurrency.py /app/api/concurrency.py
COPY api/subtitles.py /app/api/subtitles.py
COPY api/ip_whitelist.py /app/api/ip_whitelist.py
COPY api/youtube_grabber.py /app/api/youtube_grabber.py

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

# 預設啟動 API 服務
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
