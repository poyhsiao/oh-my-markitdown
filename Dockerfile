FROM python:3.12-slim

LABEL maintainer="kimhsiao"
LABEL description="MarkItDown Docker - Convert files to Markdown with all dependencies"

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴（用於處理各種文件格式）
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PDF 處理
    poppler-utils \
    # 圖片處理
    libmagic1 \
    ffmpeg \
    # 字體支持（OCR 和圖片處理）
    fonts-dejavu-core \
    tesseract-ocr \
    # 清理
    && rm -rf /var/lib/apt/lists/*

# 安裝 MarkItDown 與所有可選依賴
RUN pip install --no-cache-dir \
    'markitdown[all]' \
    markitdown-ocr

# 創建輸入/輸出目錄
RUN mkdir -p /app/input /app/output

# 設置卷標
VOLUME ["/app/input", "/app/output"]

# 默認命令：顯示幫助
CMD ["markitdown", "--help"]
