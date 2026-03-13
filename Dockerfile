FROM python:3.12-slim

LABEL maintainer="kimhsiao"
LABEL description="MarkItDown Docker with API - Convert files to Markdown via HTTP API"

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PDF 處理
    poppler-utils \
    # 圖片處理
    libmagic1 \
    ffmpeg \
    # 字體支持
    fonts-dejavu-core \
    tesseract-ocr \
    # 清理
    && rm -rf /var/lib/apt/lists/*

# 安裝 MarkItDown 和 FastAPI
RUN pip install --no-cache-dir \
    'markitdown[all]' \
    markitdown-ocr \
    fastapi \
    uvicorn \
    python-multipart \
    aiofiles

# 創建目錄結構
RUN mkdir -p /app/input /app/output /app/api

# 複製 API 服務代碼
COPY api/main.py /app/api/main.py

# 暴露 API 端口
EXPOSE 8000

# 啟動 API 服務
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
