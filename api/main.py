from fastapi import FastAPI, File, UploadFile, HTTPException, Query, APIRouter
from fastapi.responses import Response, StreamingResponse
from markitdown import MarkItDown
import tempfile
import os
from pathlib import Path
from datetime import datetime
import io
import subprocess

# Validate environment variables on startup
from .config import validate_environment, ConfigurationError

try:
    _config = validate_environment()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    raise SystemExit(1)

# 從配置物件讀取配置
API_DEBUG = _config.api.debug
DEFAULT_OCR_LANG = _config.ocr.default_lang
ENABLE_PLUGINS_BY_DEFAULT = _config.ocr.enabled_by_default
MAX_UPLOAD_SIZE = _config.upload.max_size

# OpenAI 配置（可選）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


def ocr_image_pdf(pdf_path: str, ocr_lang: str = "chi_tra+eng") -> str:
    """
    對圖片 PDF 進行 OCR 辨識
    
    某些 PDF 是掃描件（圖片 PDF），MarkItDown 無法直接提取文字。
    此函數會：
    1. 用 PyMuPDF 將 PDF 轉換為高解析度圖片
    2. 用 Tesseract OCR 辨識圖片中的文字
    
    Args:
        pdf_path: PDF 文件路徑
        ocr_lang: OCR 語言（預設 chi_tra+eng）
    
    Returns:
        OCR 辨識出的文字內容
    """
    try:
        import fitz  # PyMuPDF
        from PIL import Image
        
        doc = fitz.open(pdf_path)
        all_text = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # 檢查頁面是否有可提取的文字
            text = page.get_text()
            if text.strip():
                # 如果有文字，直接使用
                all_text.append(f"--- Page {page_num + 1} ---\n{text}")
                continue
            
            # 沒有文字，用 OCR
            # 高解析度渲染（3x 放大）
            mat = fitz.Matrix(3, 3)
            pix = page.get_pixmap(matrix=mat)
            
            # 保存為臨時圖片
            temp_img = f"/tmp/page_{page_num}.png"
            pix.save(temp_img)
            
            # 用 Tesseract OCR
            result = subprocess.run(
                ["tesseract", temp_img, "stdout", "-l", ocr_lang],
                capture_output=True,
                text=True
            )
            
            ocr_text = result.stdout.strip()
            if ocr_text:
                all_text.append(f"--- Page {page_num + 1} (OCR) ---\n{ocr_text}")
            
            # 清理臨時圖片
            try:
                os.unlink(temp_img)
            except:
                pass
        
        doc.close()
        return "\n\n".join(all_text)
    
    except Exception as e:
        raise Exception(f"OCR 處理失敗: {str(e)}")

app = FastAPI(
    title="MarkItDown API",
    description="Convert various file formats to Markdown via HTTP API with multi-language OCR support and YouTube/Audio transcription",
    version="0.1.0",
    debug=API_DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 創建 API Router with /api/v1 prefix
api_router = APIRouter(prefix="/api/v1")

# 配置 servers 讓 Swagger 知道正確的 API 端點
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .constants import OCR_LANGUAGES

# Setup logging and add middleware
from .middleware import RequestLoggingMiddleware, setup_logging
logger = setup_logging()

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# ===== Error Handling Configuration =====
import json
from fastapi.exceptions import RequestValidationError

ERROR_LANG = os.getenv("ERROR_LANG", "zh-TW")

ERROR_MESSAGES = {
    "zh-TW": {
        "internal_error": "伺服器內部錯誤，請稍後重試",
        "not_found": "找不到資源",
        "validation_error": "請求參數驗證失敗",
        "timeout": "操作超時，請稍後重試",
    },
    "en": {
        "internal_error": "Internal server error, please try again later",
        "not_found": "Resource not found",
        "validation_error": "Request validation failed",
        "timeout": "Operation timed out, please try again later",
    }
}

def get_error_message(key: str, accept_language: str = None) -> str:
    """Get error message in preferred language."""
    lang = accept_language if accept_language else ERROR_LANG
    if lang not in ERROR_MESSAGES:
        lang = "en"  # Fallback to English
    return ERROR_MESSAGES.get(lang, {}).get(key, "Unknown error")

# ===== Exception Handlers =====
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Handle unhandled exceptions with language-aware messages."""
    if API_DEBUG:
        # Debug mode: show full error details
        return Response(
            content=json.dumps({
                "detail": str(exc),
                "type": type(exc).__name__,
            }),
            status_code=500,
            media_type="application/json"
        )
    else:
        # Production mode: hide internal details
        accept_language = request.headers.get("Accept-Language", ERROR_LANG)
        message = get_error_message("internal_error", accept_language)
        
        # Log full error internally
        logger.error(f"Internal error: {exc}", exc_info=True)
        
        return Response(
            content=json.dumps({"detail": message}),
            status_code=500,
            media_type="application/json"
        )

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Return empty 404 response."""
    return Response(status_code=404)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors with language-aware messages."""
    accept_language = request.headers.get("Accept-Language", ERROR_LANG)
    message = get_error_message("validation_error", accept_language)
    
    return Response(
        content=json.dumps({
            "detail": message,
            "errors": exc.errors() if API_DEBUG else None
        }),
        status_code=400,
        media_type="application/json"
    )

# Initialize MarkItDown
from fastapi.responses import Response

md = MarkItDown(enable_plugins=ENABLE_PLUGINS_BY_DEFAULT)

@app.get("/", include_in_schema=False)
async def root():
    """Return 404 for root path."""
    return Response(status_code=404)

# Mount system router
from .system import api_router as system_router
app.include_router(system_router)

# Keep health endpoint
@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "ok"}

@api_router.post("/convert", 
          summary="Convert file to Markdown",
          description="上傳文件並轉換為 Markdown 格式\n\n"
                      "**支援的文件格式：**\n"
                      "- PDF, DOCX, DOC, PPTX, PPT\n"
                      "- XLSX, XLS\n"
                      "- 圖片（JPG, PNG, GIF, WEBP 等）\n"
                      "- 音頻（MP3, WAV, M4A 等）\n"
                      "- HTML, CSV, JSON, XML\n"
                      "- ZIP, EPub\n\n"
                      "**OCR 語言支援：**\n"
                      "- chi_tra: 繁體中文\n"
                      "- chi_sim: 簡體中文\n"
                      "- eng: 英文\n"
                      "- jpn: 日文\n"
                      "- kor: 韓文\n"
                      "- tha: 泰文\n"
                      "- vie: 越南文\n\n"
                      "**回傳格式：**\n"
                      "- markdown: 直接回傳 Markdown 文字\n"
                      "- json: 回傳 JSON 包含 metadata 和內容")
async def convert_file(
    file: UploadFile = File(..., description="要轉換的文件檔案"),
    enable_plugins: bool = Query(False, description="是否啟用插件（如 OCR），預設 false"),
    ocr_lang: str = Query("chi_tra+eng", description="OCR 語言代碼，預設 chi_tra+eng，可用 + 組合多種語言"),
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
        # 重要：使用 delete=False 並手動管理，確保編碼正確
        import uuid
        temp_filename = f"temp_{uuid.uuid4().hex}{file_ext}"
        temp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(temp_dir, temp_filename)
        
        try:
            # 以二進制模式寫入文件（避免編碼問題）
            with open(tmp_path, 'wb') as tmp_file:
                tmp_file.write(file_content)
            
            # 執行轉換（如需 OCR，設置環境變數）
            env_vars = {}
            if enable_plugins and ocr_lang:
                env_vars['TESSERACT_LANG'] = ocr_lang
            
            result = md.convert(tmp_path, enable_plugins=enable_plugins)
            text_content = result.text_content
            
            # 特殊處理：如果是 PDF 且內容為空，可能是圖片 PDF（掃描件）
            # 需要用 OCR 辨識
            if file_ext == '.pdf' and (not text_content or len(text_content.strip()) < 10):
                if API_DEBUG:
                    print(f"PDF 內容為空或少於 10 字元，嘗試 OCR 辨識...")
                
                try:
                    ocr_result = ocr_image_pdf(tmp_path, ocr_lang or DEFAULT_OCR_LANG)
                    if ocr_result and len(ocr_result.strip()) > len(text_content.strip()):
                        text_content = f"[OCR 辨識結果]\n\n{ocr_result}"
                        if API_DEBUG:
                            print(f"OCR 辨識成功：{len(text_content)} 字元")
                except Exception as ocr_error:
                    if API_DEBUG:
                        print(f"OCR 辨識失敗：{ocr_error}")
            
            # 特殊處理：如果是圖片且啟用 OCR，用 Tesseract 辨識
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
            if file_ext in image_extensions and enable_plugins:
                if API_DEBUG:
                    print(f"圖片 OCR 辨識...")
                
                try:
                    ocr_result = subprocess.run(
                        ["tesseract", tmp_path, "stdout", "-l", ocr_lang or DEFAULT_OCR_LANG],
                        capture_output=True,
                        text=True
                    )
                    ocr_text = ocr_result.stdout.strip()
                    if ocr_text and len(ocr_text) > len(text_content.strip()):
                        text_content = f"[OCR 辨識結果]\n\n{ocr_text}"
                        if API_DEBUG:
                            print(f"圖片 OCR 成功：{len(text_content)} 字元")
                except Exception as ocr_error:
                    if API_DEBUG:
                        print(f"圖片 OCR 失敗：{ocr_error}")
            
            if return_format == "markdown":
                # 直接回傳 Markdown 文字（確保 UTF-8 編碼）
                # HTTP headers 必須是 ASCII/latin-1，不能包含中文
                # 使用 URL encoding 處理文件名
                from urllib.parse import quote
                safe_filename = quote(file.filename or "unknown", safe='')
                
                return Response(
                    content=text_content.encode('utf-8'),
                    media_type="text/markdown; charset=utf-8",
                    headers={
                        "X-Original-Filename": safe_filename,
                        "X-Conversion-Time": datetime.now().isoformat(),
                        "X-OCR-Language": ocr_lang if enable_plugins else "N/A",
                        # 文件名使用 ASCII 安全字符，避免編碼問題
                        "Content-Disposition": f'attachment; filename="converted.md"'
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
                    "content": text_content,
                    "metadata": {
                        "type": getattr(result, 'type', 'unknown'),
                        "source": getattr(result, 'source', None),
                        "title": getattr(result, 'title', None),
                        "author": getattr(result, 'author', None),
                    }
                }
        
        finally:
            # 清理臨時文件
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception as cleanup_error:
                    if API_DEBUG:
                        print(f"清理臨時文件失敗：{cleanup_error}")
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"轉換失敗：{str(e)}"
        )

# ==================== Whisper 轉錄端點 ====================

from .whisper_transcribe import (
    transcribe_audio,
    transcribe_youtube_video,
    format_transcript_as_markdown,
    SUPPORTED_LANGUAGES
)

@api_router.post("/convert/youtube")
async def transcribe_youtube(
    url: str = Query(..., description="YouTube 影片 URL"),
    language: str = Query("zh", description="語言代碼（zh, en, ja, ko 等）"),
    model_size: str = Query("base", description="模型大小（tiny, base, small, medium, large）"),
    return_format: str = Query("markdown", description="回傳格式：markdown 或 json"),
    include_metadata: bool = Query(True, description="是否包含元數據")
):
    """
    下載 YouTube 影片音訊並使用 Whisper 轉錄
    
    - **url**: YouTube 影片 URL
    - **language**: 語言代碼（zh=中文, en=英文, ja=日文, ko=韓文）
    - **model_size**: 模型大小（tiny 最快, large 最準確）
    - **return_format**: 回傳格式
    - **include_metadata**: 是否包含轉錄元數據
    """
    
    try:
        # 轉錄 YouTube 影片
        result = transcribe_youtube_video(
            url=url,
            language=language,
            model_size=model_size
        )
        
        # 格式化為 Markdown
        markdown_content = format_transcript_as_markdown(
            title=result["title"],
            transcript=result["transcript"],
            metadata=result["metadata"],
            include_metadata=include_metadata
        )
        
        if return_format == "markdown":
            return Response(
                content=markdown_content.encode('utf-8'),
                media_type="text/markdown; charset=utf-8",
                headers={
                    "X-Source-URL": url,
                    "X-Conversion-Time": datetime.now().isoformat(),
                    "X-Transcript-Length": str(len(result["transcript"]))
                }
            )
        else:
            return {
                "success": True,
                "url": url,
                "title": result["title"],
                "transcript": result["transcript"],
                "metadata": result["metadata"],
                "markdown": markdown_content
            }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"轉錄失敗：{str(e)}"
        )


@api_router.post("/convert/audio")
async def transcribe_audio_file(
    file: UploadFile = File(..., description="音訊檔案"),
    language: str = Query("zh", description="語言代碼"),
    model_size: str = Query("base", description="模型大小"),
    return_format: str = Query("markdown", description="回傳格式")
):
    """
    上傳音訊檔案並使用 Whisper 轉錄
    
    - **file**: 音訊檔案（MP3, WAV, M4A, FLAC 等）
    - **language**: 語言代碼
    - **model_size**: 模型大小
    - **return_format**: 回傳格式
    """
    
    try:
        # 保存上傳的檔案
        suffix = Path(file.filename or "").suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # 轉錄
            transcript, metadata = transcribe_audio(
                tmp_path,
                language=language,
                model_size=model_size
            )
            
            # 格式化
            markdown_content = format_transcript_as_markdown(
                title=file.filename or "音訊轉錄",
                transcript=transcript,
                metadata=metadata
            )
            
            if return_format == "markdown":
                return Response(
                    content=markdown_content.encode('utf-8'),
                    media_type="text/markdown; charset=utf-8",
                    headers={
                        "X-Filename": file.filename or "unknown",
                        "X-Conversion-Time": datetime.now().isoformat()
                    }
                )
            else:
                return {
                    "success": True,
                    "filename": file.filename,
                    "transcript": transcript,
                    "metadata": metadata,
                    "markdown": markdown_content
                }
        
        finally:
            # 清理臨時檔案
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"轉錄失敗：{str(e)}"
        )


@api_router.get("/convert/languages")
async def list_transcribe_languages():
    """列出 Whisper 支援的語言"""
    return {
        "supported_languages": SUPPORTED_LANGUAGES,
        "models": {
            "tiny": {"speed": "最快", "accuracy": "一般", "memory": "~500MB"},
            "base": {"speed": "快", "accuracy": "好", "memory": "~1GB"},
            "small": {"speed": "中等", "accuracy": "很好", "memory": "~2GB"},
            "medium": {"speed": "慢", "accuracy": "極好", "memory": "~5GB"},
            "large": {"speed": "最慢", "accuracy": "最佳", "memory": "~10GB"}
        },
        "recommended": {
            "fast": "tiny",
            "balanced": "base",
            "accurate": "small"
        }
    }

@api_router.get("/formats")
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

@api_router.get("/ocr-languages")
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

@api_router.get("/config")
async def get_config():
    """獲取當前 API 配置（敏感信息已隱藏）"""
    return {
        "api": {
            "version": "0.1.0",
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

# 註冊 API Router
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT_INTERNAL", "8000"))
    )
