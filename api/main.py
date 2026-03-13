from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from markitdown import MarkItDown
import tempfile
import os
from pathlib import Path
from datetime import datetime
import io

# 從環境變數讀取配置
API_DEBUG = os.getenv("API_DEBUG", "false").lower() == "true"
DEFAULT_OCR_LANG = os.getenv("DEFAULT_OCR_LANG", "chi_tra+eng")
ENABLE_PLUGINS_BY_DEFAULT = os.getenv("ENABLE_PLUGINS_BY_DEFAULT", "false").lower() == "true"
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", "52428800"))  # 預設 50MB

# OpenAI 配置（可選）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

app = FastAPI(
    title="MarkItDown API",
    description="Convert various file formats to Markdown via HTTP API with multi-language OCR support",
    version="1.1.0",
    debug=API_DEBUG
)

# 支援的 OCR 語言代碼
OCR_LANGUAGES = {
    "chi_sim": "簡體中文",
    "chi_tra": "繁體中文",
    "eng": "英文",
    "jpn": "日文",
    "kor": "韓文",
    "tha": "泰文",
    "vie": "越南文",
}

# 初始化 MarkItDown
md = MarkItDown(enable_plugins=ENABLE_PLUGINS_BY_DEFAULT)

@app.get("/")
async def root():
    """API 健康檢查"""
    return {
        "status": "healthy",
        "service": "MarkItDown API",
        "version": "1.1.0",
        "supported_formats": [
            "PDF", "DOCX", "PPTX", "XLSX", "XLS",
            "HTML", "Images", "Audio", "CSV", "JSON", "XML",
            "ZIP", "EPub", "Outlook"
        ],
        "ocr_languages": list(OCR_LANGUAGES.keys()),
        "default_ocr_lang": DEFAULT_OCR_LANG
    }

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "ok"}

@app.post("/convert")
async def convert_file(
    file: UploadFile = File(..., description="要轉換的文件檔案"),
    enable_plugins: bool = Query(None, description="是否啟用插件（如 OCR），預設使用環境變數 ENABLE_PLUGINS_BY_DEFAULT"),
    ocr_lang: str = Query(None, description=f"OCR 語言代碼，預設使用環境變數 DEFAULT_OCR_LANG ({DEFAULT_OCR_LANG})"),
    return_format: str = Query("markdown", description="回傳格式：markdown 或 json", regex="^(markdown|json)$")
):
    """
    上傳文件並轉換為 Markdown
    
    - **file**: 要轉換的文件（支援 PDF, DOCX, PPTX, XLSX, 圖片，音頻等）
    - **enable_plugins**: 是否啟用插件（預設：環境變數 ENABLE_PLUGINS_BY_DEFAULT）
    - **ocr_lang**: OCR 語言（預設：環境變數 DEFAULT_OCR_LANG，支援 chi_tra, chi_sim, eng, jpn, kor, tha, vie，可用 + 組合）
    - **return_format**: 回傳格式（markdown 或 json）
    
    回傳：
    - **markdown**: 直接回傳 Markdown 文字（Content-Type: text/markdown）
    - **json**: 回傳 JSON 包含 metadata 和內容
    """
    
    # 驗證文件大小
    file_content = await file.read()
    if len(file_content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"文件過大：{len(file_content)} 字節。最大限制：{MAX_UPLOAD_SIZE} 字節 ({MAX_UPLOAD_SIZE // 1024 // 1024}MB)"
        )
    
    # 驗證文件類型
    allowed_extensions = {
        '.pdf', '.docx', '.doc', '.pptx', '.ppt', 
        '.xlsx', '.xls', '.html', '.htm', '.csv',
        '.json', '.xml', '.zip', '.epub', '.msg',
        '.jpg', '.jpeg', '.png', '.gif', '.webp',
        '.mp3', '.wav', '.m4a', '.flac'
    }
    
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支援的文件類型：{file_ext}。支援的類型：{', '.join(allowed_extensions)}"
        )
    
    # 使用環境變數預設值
    if enable_plugins is None:
        enable_plugins = ENABLE_PLUGINS_BY_DEFAULT
    
    if ocr_lang is None:
        ocr_lang = DEFAULT_OCR_LANG
    
    # 驗證 OCR 語言
    if ocr_lang:
        valid_langs = set(OCR_LANGUAGES.keys())
        requested_langs = ocr_lang.split('+')
        for lang in requested_langs:
            if lang not in valid_langs:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支援的 OCR 語言：{lang}。支援的語言：{', '.join(valid_langs)}"
                )
    
    try:
        # 使用臨時文件進行轉換（MarkItDown 需要文件路徑）
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name
        
        try:
            # 執行轉換（如需 OCR，設置環境變數）
            env_vars = {}
            if enable_plugins and ocr_lang:
                env_vars['TESSERACT_LANG'] = ocr_lang
            
            result = md.convert(tmp_path, enable_plugins=enable_plugins)
            
            if return_format == "markdown":
                # 直接回傳 Markdown 文字
                return Response(
                    content=result.text_content,
                    media_type="text/markdown",
                    headers={
                        "X-Original-Filename": file.filename or "unknown",
                        "X-Conversion-Time": datetime.now().isoformat(),
                        "X-OCR-Language": ocr_lang if enable_plugins else "N/A",
                        "Content-Disposition": f'attachment; filename="{Path(file.filename or "").stem}.md"'
                    }
                )
            else:
                # 回傳 JSON 格式
                return {
                    "success": True,
                    "filename": file.filename,
                    "file_size": len(file_content),
                    "conversion_time": datetime.now().isoformat(),
                    "ocr_language": ocr_lang if enable_plugins else "N/A",
                    "content": result.text_content,
                    "metadata": {
                        "type": result.type,
                        "source": result.source,
                        "title": getattr(result, 'title', None),
                        "author": getattr(result, 'author', None),
                    }
                }
        
        finally:
            # 清理臨時文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"轉換失敗：{str(e)}"
        )

@app.post("/convert/url")
async def convert_url(
    url: str = Query(..., description="要抓取的網頁 URL"),
    return_format: str = Query("markdown", description="回傳格式：markdown 或 json")
):
    """
    從 URL 抓取內容並轉換為 Markdown
    
    - **url**: 網頁 URL 或 YouTube URL
    - **return_format**: 回傳格式（markdown 或 json）
    """
    
    try:
        result = md.convert(url)
        
        if return_format == "markdown":
            return Response(
                content=result.text_content,
                media_type="text/markdown",
                headers={
                    "X-Source-URL": url,
                    "X-Conversion-Time": datetime.now().isoformat()
                }
            )
        else:
            return {
                "success": True,
                "url": url,
                "conversion_time": datetime.now().isoformat(),
                "content": result.text_content,
                "metadata": {
                    "type": result.type,
                    "source": result.source,
                    "title": getattr(result, 'title', None),
                }
            }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"轉換失敗：{str(e)}"
        )

@app.get("/formats")
async def list_formats():
    """列出所有支援的文件格式"""
    return {
        "documents": ["PDF", "DOCX", "DOC", "PPTX", "PPT", "XLSX", "XLS", "ODT", "ODS", "ODP"],
        "web": ["HTML", "HTM", "URL"],
        "images": ["JPG", "JPEG", "PNG", "GIF", "WEBP", "BMP", "TIFF"],
        "audio": ["MP3", "WAV", "M4A", "FLAC", "OGG"],
        "data": ["CSV", "JSON", "XML"],
        "other": ["ZIP", "EPUB", "MSG", "OUTLOOK"]
    }

@app.get("/ocr-languages")
async def list_ocr_languages():
    """列出所有支援的 OCR 語言"""
    return {
        "supported_languages": OCR_LANGUAGES,
        "default": DEFAULT_OCR_LANG,
        "usage": "使用 + 符號組合多種語言，例如：chi_tra+eng+jpn",
        "examples": [
            {"code": "chi_tra", "name": "繁體中文"},
            {"code": "chi_sim", "name": "簡體中文"},
            {"code": "eng", "name": "英文"},
            {"code": "jpn", "name": "日文"},
            {"code": "kor", "name": "韓文"},
            {"code": "tha", "name": "泰文"},
            {"code": "vie", "name": "越南文"},
            {"code": "chi_tra+eng", "name": "繁體中文 + 英文（預設）"},
            {"code": "chi_sim+eng", "name": "簡體中文 + 英文"},
            {"code": "chi_tra+jpn+kor+eng", "name": "多語言混合"},
            {"code": "tha+eng", "name": "泰文 + 英文"},
            {"code": "vie+eng", "name": "越南文 + 英文"},
            {"code": "chi_tra+tha+vie+eng", "name": "東南亞多語言混合"},
        ]
    }

@app.get("/config")
async def get_config():
    """獲取當前 API 配置（敏感信息已隱藏）"""
    return {
        "api": {
            "version": "1.1.0",
            "debug": API_DEBUG,
            "max_upload_size": MAX_UPLOAD_SIZE,
            "max_upload_size_mb": MAX_UPLOAD_SIZE // 1024 // 1024,
        },
        "ocr": {
            "default_language": DEFAULT_OCR_LANG,
            "plugins_enabled_by_default": ENABLE_PLUGINS_BY_DEFAULT,
            "supported_languages": OCR_LANGUAGES,
        },
        "openai": {
            "configured": bool(OPENAI_API_KEY),
            "model": OPENAI_MODEL if OPENAI_API_KEY else "N/A",
            "base_url": OPENAI_BASE_URL if OPENAI_API_KEY else "N/A",
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT_INTERNAL", "8000"))
    )
