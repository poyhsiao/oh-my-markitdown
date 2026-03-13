FROM python:3.12-slim

LABEL maintainer="kimhsiao"
LABEL description="MarkItDown Docker with API - Convert files to Markdown via HTTP API with multi-language OCR"

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴
# 參考：https://github.com/microsoft/markitdown + 額外工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 基礎工具
    curl \
    ca-certificates \
    wget \
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
    # yt-dlp 依賴（YouTube 下載和字幕抓取）
    python3-pip \
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
    # YouTube 字幕抓取工具
    yt-dlp

# 創建目錄結構
RUN mkdir -p /app/input /app/output /app/data /app/api

# 複製 API 服務代碼
COPY api/main.py /app/api/main.py

# 複製自動轉換腳本
COPY api/auto_convert.py /app/api/auto_convert.py

# 複製 YouTube 字幕抓取工具
COPY api/youtube_grabber.py /app/api/youtube_grabber.py

# 複製 CLI 工具
COPY cli.py /app/cli.py

# 設置執行權限
RUN chmod +x /app/cli.py /app/api/youtube_grabber.py

# 暴露 API 端口
EXPOSE 8000

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 預設啟動 API 服務
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
