# Troubleshooting

Common issues and solutions for MarkItDown API.

## Table of Contents

- [Container Issues](#container-issues)
- [Conversion Issues](#conversion-issues)
- [OCR Quality Issues](#ocr-quality-issues)
- [Memory Issues](#memory-issues)
- [Upload Issues](#upload-issues)
- [Audio/Video Issues](#audiovideo-issues)

---

## Container Issues

### Container Won't Start

**Symptoms:**
- Container exits immediately after starting
- Cannot connect to API

**Solutions:**

```bash
# View logs
docker compose logs markitdown-api

# Check if port is occupied
lsof -i :51083

# Force stop and restart
docker compose down
docker compose up -d
```

**Common causes:**
1. **Port conflict** - Another service is using port 51083
2. **Missing dependencies** - Docker image needs rebuild
3. **Volume mount issues** - Check data directory permissions

### Container Keeps Restarting

**Check logs:**
```bash
docker compose logs -f markitdown-api
```

**Common causes:**
1. **Insufficient memory** - Increase `MEMORY_LIMIT`
2. **Permission issues** - Check volume mount permissions
3. **Configuration errors** - Validate `.env` file

---

## Conversion Issues

### Conversion Failed

**Check supported formats:**
```bash
curl http://localhost:51083/api/v1/formats
```

**View container logs:**
```bash
docker compose logs -f
```

**Confirm file size:**
```bash
ls -lh your-file.pdf
```

**View API configuration:**
```bash
curl http://localhost:51083/api/v1/config
```

### Empty Output

**Possible causes:**
1. **OCR not enabled** - Add `enable_plugins=true`
2. **Wrong OCR language** - Check `ocr_lang` parameter
3. **Scanned PDF** - Requires OCR processing

**Solution:**
```bash
curl -X POST "http://localhost:51083/api/v1/convert" \
  -F "file=@scanned-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+eng" \
  -o output.md
```

### File Format Not Supported

**Check supported formats:**
```bash
curl http://localhost:51083/api/v1/formats
```

**Supported formats:**
| Type | Formats |
|------|---------|
| Documents | PDF, DOCX, DOC, PPTX, PPT, XLSX, XLS, MSG |
| Web | HTML, URLs |
| Images | JPG, PNG, GIF, WEBP, BMP, TIFF |
| Audio | MP3, WAV, M4A, FLAC, OGG |
| Data | CSV, JSON, XML |
| Other | ZIP, EPub |

---

## OCR Quality Issues

### Poor OCR Quality

**Solutions:**

1. **Increase language combination:**
   ```bash
   # Use more languages for mixed documents
   -F "ocr_lang=chi_tra+eng+jpn"
   ```

2. **Use OpenAI Vision model:**
   ```bash
   # .env file
   OPENAI_API_KEY=sk-your-api-key-here
   OPENAI_MODEL=gpt-4o
   ```

3. **Improve scan quality:**
   - Ensure original document is clear
   - Increase DPI when scanning (300+ recommended)
   - Avoid skewed or rotated images

4. **Check Tesseract language packs:**
   ```bash
   docker compose exec markitdown-api bash
   tesseract --list-langs
   ```

### Missing Characters

**Possible causes:**
1. **Wrong language code** - Use correct OCR language
2. **Font not supported** - Try different OCR engine
3. **Image quality** - Increase scan resolution

**Solution:**
```bash
# Try all supported Asian languages
-F "ocr_lang=chi_tra+chi_sim+eng+jpn+kor+tha+vie"
```

### Mixed Language Documents

**Use multiple languages:**
```bash
# Northeast Asian documents
-F "ocr_lang=chi_tra+jpn+kor+eng"

# Southeast Asian documents
-F "ocr_lang=chi_tra+tha+vie+eng"
```

---

## Memory Issues

### Insufficient Memory

**Symptoms:**
- Container crashes during conversion
- Slow performance
- Out of memory errors

**Solution:**
```bash
# Increase memory limit in .env
MEMORY_LIMIT=4G
CPU_LIMIT=4.0

# Restart services
docker compose down
docker compose up -d
```

### Whisper Model Memory

**Symptoms:**
- Transcription fails
- Container becomes unresponsive

**Solution:**
```bash
# Use smaller model
WHISPER_MODEL=base  # or tiny

# Or increase memory
MEMORY_LIMIT=8G
```

**Model memory requirements:**
| Model | Memory |
|-------|--------|
| tiny | ~500MB |
| base | ~1GB |
| small | ~2GB |
| medium | ~5GB |
| large | ~10GB |

---

## Upload Issues

### Upload File Too Large

**Symptoms:**
- 413 error
- Upload fails silently

**Solution:**
```bash
# Increase upload limit in .env
MAX_UPLOAD_SIZE=104857600  # 100MB

# Restart services
docker compose restart
```

### Upload Timeout

**Symptoms:**
- Request times out
- Partial upload

**Solutions:**
1. **Increase timeout** in client
2. **Use smaller files**
3. **Check network connection**

### Invalid File Format

**Check file type:**
```bash
file your-file.pdf
```

**Ensure correct MIME type:**
```bash
# Correct way to upload
curl -X POST "http://localhost:51083/api/v1/convert" \
  -F "file=@document.pdf;type=application/pdf"
```

---

## Audio/Video Issues

### YouTube Download Failed

**Possible causes:**
1. **Video is private or age-restricted**
2. **Region-locked content**
3. **Network issues**

**Solutions:**
```bash
# Try with different model size
curl -X POST "http://localhost:51083/api/v1/convert/youtube?url=...&model_size=base"
```

### Audio Transcription Quality

**Improve accuracy:**
1. **Specify correct language:**
   ```bash
   -F "language=zh"  # Chinese
   -F "language=en"  # English
   ```

2. **Use larger model:**
   ```bash
   -F "model_size=small"  # Better accuracy
   ```

3. **Ensure audio quality:**
   - Clear speech
   - Minimal background noise
   - Proper sample rate

### No Audio Detected

**Check audio format:**
```bash
# Verify file
ffprobe audio.mp3
```

**Supported formats:**
- MP3, WAV, M4A, FLAC, OGG

---

## Debug Mode

### Enable Debug Mode

```bash
# .env file
API_DEBUG=true

# Restart
docker compose restart

# View detailed logs
docker compose logs -f markitdown-api
```

### Check System Status

```bash
# Health check
curl http://localhost:51083/health

# Configuration
curl http://localhost:51083/api/v1/config

# Storage usage
curl http://localhost:51083/api/v1/admin/storage

# Queue status
curl http://localhost:51083/api/v1/admin/queue
```

---

## Getting Help

### Collect Diagnostic Information

```bash
# System information
docker compose logs markitdown-api > logs.txt
curl http://localhost:51083/api/v1/config > config.json
docker compose exec markitdown-api pip list > packages.txt

# Test dependencies
./scripts/test-deps.sh
```

### Useful Resources

- [MarkItDown GitHub](https://github.com/microsoft/markitdown)
- [Tesseract OCR Documentation](https://tesseract-ocr.github.io/)
- [Faster-Whisper Documentation](https://github.com/SYSTRAN/faster-whisper)

---

## Related Documentation

- [API Reference](API_REFERENCE.md) - Complete API endpoint documentation
- [Code Examples](CODE_EXAMPLES.md) - Practical code examples
- [Advanced Configuration](ADVANCED_CONFIG.md) - OpenAI, Azure, Docker configuration