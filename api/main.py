from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from markitdown import MarkItDown
import tempfile
import os
from pathlib import Path
from datetime import datetime
import io

app = FastAPI(
    title="MarkItDown API",
    description="Convert various file formats to Markdown via HTTP API",
    version="1.0.0"
)

# 初始化 MarkItDown
md = MarkItDown(enable_plugins=False)

@app.get("/")
async def root():
    """API 健康檢查"""
    return {
        "status": "healthy",
        "service": "MarkItDown API",
        "version": "1.0.0",
        "supported_formats": [
            "PDF", "DOCX", "PPTX", "XLSX", "XLS",
            "HTML", "Images", "Audio", "CSV", "JSON", "XML",
            "ZIP", "EPub", "Outlook"
        ]
    }

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "ok"}

@app.post("/convert")
async def convert_file(
    file: UploadFile = File(..., description="要轉換的文件檔案"),
    enable_plugins: bool = Query(False, description="是否啟用插件（如 OCR）"),
    return_format: str = Query("markdown", description="回傳格式：markdown 或 json", regex="^(markdown|json)$")
):
    """
    上傳文件並轉換為 Markdown
    
    - **file**: 要轉換的文件（支援 PDF, DOCX, PPTX, XLSX, 圖片，音頻等）
    - **enable_plugins**: 是否啟用插件（預設 false）
    - **return_format**: 回傳格式（markdown 或 json）
    
    回傳：
    - **markdown**: 直接回傳 Markdown 文字（Content-Type: text/markdown）
    - **json**: 回傳 JSON 包含 metadata 和內容
    """
    
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
    
    try:
        # 讀取上傳的文件
        file_content = await file.read()
        
        # 使用臨時文件進行轉換（MarkItDown 需要文件路徑）
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name
        
        try:
            # 執行轉換
            result = md.convert(tmp_path, enable_plugins=enable_plugins)
            
            if return_format == "markdown":
                # 直接回傳 Markdown 文字
                return Response(
                    content=result.text_content,
                    media_type="text/markdown",
                    headers={
                        "X-Original-Filename": file.filename or "unknown",
                        "X-Conversion-Time": datetime.now().isoformat(),
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
