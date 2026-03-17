"""
Modified version of main.py with concurrency control integration.
This shows how to integrate ConcurrencyManager into API endpoints.
"""

# Original convert_file_endpoint with concurrency control added
async def convert_file_endpoint_with_concurrency(
    file: UploadFile = File(..., description="File to convert"),
    enable_ocr: bool = Query(False, description="Enable OCR, default false"),
    ocr_lang: str = Query("chi_tra+eng", description="OCR language code, default chi_tra+eng, use + to combine multiple languages"),
    return_format: str = Query("markdown", description="Return format: markdown or json", regex="^(markdown|json)$")
):
    """
    Upload file and convert to Markdown
    
    - **file**: File to convert (supports PDF, DOCX, PPTX, XLSX, images, audio, etc.)
    - **enable_ocr**: Enable OCR (default: false)
    - **ocr_lang**: OCR language (default: env var DEFAULT_OCR_LANG, supports chi_tra, chi_sim, eng, jpn, kor, tha, vie, use + to combine)
    - **return_format**: Return format (markdown or json)
    
    Returns:
    - **markdown**: Returns Markdown text directly (Content-Type: text/markdown)
    - **json**: Returns JSON with metadata and content
    """
    
    # Set request ID
    request_id = set_request_id()
    
    # Validate file size
    file_content = await file.read()
    if len(file_content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=error_response(
                code=ErrorCodes.FILE_TOO_LARGE,
                message=f"File too large: {len(file_content)} bytes. Maximum allowed: {MAX_UPLOAD_SIZE} bytes ({MAX_UPLOAD_SIZE // 1024 // 1024}MB)",
                request_id=request_id
            )
        )
    
    # Validate file type
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
            detail=error_response(
                code=ErrorCodes.UNSUPPORTED_FORMAT,
                message=f"Unsupported file type: {file_ext}. Supported types: {', '.join(allowed_extensions)}",
                request_id=request_id
            )
        )
    
    # Use environment variable defaults
    enable_plugins = enable_ocr  # Use enable_ocr parameter (spec-compliant name)
    
    if ocr_lang is None:
        ocr_lang = DEFAULT_OCR_LANG
    
    # Validate OCR language
    if ocr_lang:
        valid_langs = set(OCR_LANGUAGES.keys())
        requested_langs = ocr_lang.split('+')
        for lang in requested_langs:
            if lang not in valid_langs:
                raise HTTPException(
                    status_code=400,
                    detail=error_response(
                        code=ErrorCodes.INVALID_OCR_LANGUAGE,
                        message=f"Unsupported OCR language: {lang}. Supported languages: {', '.join(valid_langs)}",
                        request_id=request_id
                    )
                )
    
    # ===== CONCURRENCY CONTROL INTEGRATION =====
    # Get concurrency manager
    manager = get_concurrency_manager()
    
    # Wait for processing slot with timeout
    acquired, queue_item = await manager.wait_for_slot(
        request_type="convert",
        request_id=request_id,
        timeout=None  # Use default queue_timeout from config
    )
    
    if not acquired:
        # Queue is full, return queue waiting response
        from .response import queue_waiting_response
        from fastapi.responses import JSONResponse
        
        # Calculate estimated wait time based on queue position
        estimated_wait = 30  # Default 30 seconds
        if queue_item:
            estimated_wait = queue_item.position * 10  # 10 seconds per position
        
        return JSONResponse(
            status_code=202,
            content=queue_waiting_response(
                queue_position=queue_item.position if queue_item else 1,
                estimated_wait_seconds=estimated_wait,
                current_processing=manager.current_processing,
                max_concurrent=manager.max_concurrent,
                request_id=request_id
            )
        )
    
    # Slot acquired, proceed with processing
    try:
        # Use temporary file for conversion (MarkItDown requires file path)
        # Important: Use delete=False and manage manually to ensure correct encoding
        import uuid
        temp_filename = f"temp_{uuid.uuid4().hex}{file_ext}"
        temp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(temp_dir, temp_filename)
        
        try:
            # Write file in binary mode (avoid encoding issues)
            with open(tmp_path, 'wb') as tmp_file:
                tmp_file.write(file_content)
            
            # Execute conversion (set environment variable if OCR needed)
            env_vars = {}
            if enable_plugins and ocr_lang:
                env_vars['TESSERACT_LANG'] = ocr_lang
            
            result = md.convert(tmp_path, enable_plugins=enable_plugins)
            text_content = result.text_content
            
            # Special handling: If PDF and content is empty, may be image PDF (scanned)
            # Need OCR processing
            if file_ext == '.pdf' and (not text_content or len(text_content.strip()) < 10):
                if API_DEBUG:
                    print(f"PDF content is empty or less than 10 characters, attempting OCR...")
                
                try:
                    ocr_result = ocr_image_pdf(tmp_path, ocr_lang or DEFAULT_OCR_LANG)
                    if ocr_result and len(ocr_result.strip()) > len(text_content.strip()):
                        text_content = f"[OCR Result]\n\n{ocr_result}"
                        if API_DEBUG:
                            print(f"OCR successful: {len(text_content)} characters")
                except Exception as ocr_error:
                    if API_DEBUG:
                        print(f"OCR failed: {ocr_error}")
            
            # Special handling: If image and OCR enabled, use Tesseract
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
            if file_ext in image_extensions and enable_plugins:
                if API_DEBUG:
                    print(f"Image OCR processing...")
                
                try:
                    ocr_result = subprocess.run(
                        ["tesseract", tmp_path, "stdout", "-l", ocr_lang or DEFAULT_OCR_LANG],
                        capture_output=True,
                        text=True
                    )
                    ocr_text = ocr_result.stdout.strip()
                    if ocr_text and len(ocr_text) > len(text_content.strip()):
                        text_content = f"[OCR Result]\n\n{ocr_text}"
                        if API_DEBUG:
                            print(f"Image OCR successful: {len(text_content)} characters")
                except Exception as ocr_error:
                    if API_DEBUG:
                        print(f"Image OCR failed: {ocr_error}")
            
            if return_format == "markdown":
                # Return Markdown text directly (ensure UTF-8 encoding)
                # HTTP headers must be ASCII/latin-1, cannot contain Chinese
                # Use URL encoding for filename
                from urllib.parse import quote
                safe_filename = quote(file.filename or "unknown", safe='')
                
                return Response(
                    content=text_content.encode('utf-8'),
                    media_type="text/markdown; charset=utf-8",
                    headers={
                        "X-Original-Filename": safe_filename,
                        "X-Conversion-Time": datetime.now().isoformat(),
                        "X-OCR-Language": ocr_lang if enable_plugins else "N/A",
                        # Filename uses ASCII-safe characters to avoid encoding issues
                        "Content-Disposition": f'attachment; filename="converted.md"'
                    }
                )
            else:
                # Return JSON format (using unified response format)
                return convert_file_response(
                    content=text_content,
                    format="markdown",
                    filename=file.filename or "unknown",
                    file_size=len(file_content),
                    conversion_time=datetime.now().isoformat(),
                    ocr_language=ocr_lang if enable_plugins else None,
                    request_id=request_id
                )
        
        finally:
            # Cleanup temporary file
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception as cleanup_error:
                    if API_DEBUG:
                        print(f"Failed to cleanup temporary file: {cleanup_error}")
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=error_response(
                code=ErrorCodes.INTERNAL_ERROR,
                message=f"Conversion failed: {str(e)}",
                request_id=request_id
            )
        )
    finally:
        # Always release the processing slot
        manager.release(request_id)

