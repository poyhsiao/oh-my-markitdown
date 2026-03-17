# Advanced Configuration

Advanced configuration options for MarkItDown API including OpenAI Vision, Azure Document Intelligence, and Docker customization.

## Table of Contents

- [OpenAI Vision Model](#openai-vision-model)
- [Azure Document Intelligence](#azure-document-intelligence)
- [Batch Processing](#batch-processing)
- [Custom Docker Configuration](#custom-docker-configuration)

---

## OpenAI Vision Model

For higher quality OCR (especially for complex documents or low-quality scans), use OpenAI vision model.

### 1. Configure Environment Variables

```bash
# .env file
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

### 2. Restart Services

```bash
docker compose restart
```

### 3. Verify Configuration

```bash
curl http://localhost:51083/api/v1/config
```

### 4. Python Usage Example

```python
from markitdown import MarkItDown
from openai import OpenAI

client = OpenAI(
    api_key="sk-your-api-key-here",
    base_url="https://api.openai.com/v1"
)

md = MarkItDown(
    enable_plugins=True,
    llm_client=client,
    llm_model="gpt-4o"
)

result = md.convert("scanned-document.pdf")
print(result.text_content)
```

### When to Use OpenAI Vision

- **Complex documents** with mixed layouts
- **Low-quality scans** that Tesseract struggles with
- **Handwriting recognition**
- **Documents with unusual fonts or formatting**
- **Multi-language documents** with complex character sets

### Cost Considerations

OpenAI Vision API usage incurs costs based on image/document size. Consider:
- Use Tesseract (free) for standard documents
- Use OpenAI Vision only when quality justifies the cost
- Process documents in batches to optimize API calls

---

## Azure Document Intelligence

Azure Document Intelligence provides enterprise-grade document processing with advanced OCR and layout analysis.

### 1. Configure Environment Variables

```bash
# .env file
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-azure-key-here
```

### 2. Use Azure Conversion

```bash
curl -X POST "http://localhost:51083/api/v1/convert" \
  -F "file=@document.pdf" \
  -F "enable_plugins=true" \
  -o output.md
```

### Features

- **High accuracy OCR** for printed and handwritten text
- **Layout analysis** preserving tables, lists, and formatting
- **Key-value pair extraction** for forms
- **Multi-language support** including Asian languages
- **Enterprise security** with Azure compliance certifications

### When to Use Azure

- **Enterprise environments** requiring compliance
- **Form processing** with structured data extraction
- **High-volume document processing**
- **Regulated industries** (healthcare, finance)

---

## Batch Processing

### Directory Structure

```bash
mkdir -p input output
```

### Place Files

```bash
cp *.pdf input/
```

### Batch Convert Using Docker

```bash
# Using provided script
docker compose run --rm markitdown-api bash -c "
for file in /app/input/*.pdf; do
    filename=\$(basename \"\$file\" .pdf)
    markitdown \"\$file\" -o \"/app/output/\${filename}.md\"
    echo \"Conversion complete: \$filename.md\"
done
"
```

### Using Auto-Convert Feature

Enable auto-convert to automatically process files placed in `input/`:

```bash
# .env configuration
AUTO_ENABLED=true
AUTO_POLL_INTERVAL=5
AUTO_ENABLE_PLUGINS=true
AUTO_OCR_LANG=chi_tra+eng

# Start services
docker compose up -d

# Place files - they will be automatically converted
cp *.pdf input/

# Check output
ls output/
```

See [AUTO_CONVERT.md](../AUTO_CONVERT.md) for detailed instructions.

---

## Custom Docker Configuration

### Increase Memory Limit

```yaml
# docker-compose.yml
services:
  markitdown-api:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '4.0'
        reservations:
          memory: 1G
          cpus: '1.0'
```

### Change Logging Configuration

```yaml
# docker-compose.yml
services:
  markitdown-api:
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"
```

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| **API Configuration** |
| `API_PORT` | `51083` | External port |
| `API_PORT_INTERNAL` | `8000` | Internal container port |
| `API_HOST` | `0.0.0.0` | Listen address |
| `API_DEBUG` | `false` | Enable debug mode |
| `API_WORKERS` | `1` | Number of workers |
| **Resource Limits** |
| `MEMORY_LIMIT` | `2G` | Memory limit |
| `CPU_LIMIT` | `2.0` | CPU limit (cores) |
| **Upload Limits** |
| `MAX_UPLOAD_SIZE` | `52428800` | Max upload size (50MB) |
| **OCR Configuration** |
| `DEFAULT_OCR_LANG` | `chi_tra+eng` | Default OCR language |
| `ENABLE_PLUGINS_BY_DEFAULT` | `false` | Enable plugins by default |
| **OpenAI** |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | API endpoint |
| `OPENAI_MODEL` | `gpt-4o` | Model to use |
| **Azure** |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | - | Azure endpoint |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | - | Azure key |

### Production Configuration Example

```bash
# .env for production
API_PORT=51083
API_DEBUG=false
API_WORKERS=4

MAX_UPLOAD_SIZE=104857600  # 100MB
MEMORY_LIMIT=4G
CPU_LIMIT=4.0

DEFAULT_OCR_LANG=chi_tra+eng
ENABLE_PLUGINS_BY_DEFAULT=false

# Logging
LOG_MAX_SIZE=50m
LOG_MAX_FILE=5

# Health checks
HEALTHCHECK_INTERVAL=30s
HEALTHCHECK_TIMEOUT=10s
HEALTHCHECK_RETRIES=3
```

### Performance Tuning

**For high-throughput environments:**

1. **Increase workers** based on CPU cores:
   ```bash
   API_WORKERS=4  # Match CPU cores
   ```

2. **Adjust memory** for large files:
   ```bash
   MEMORY_LIMIT=8G
   MAX_UPLOAD_SIZE=209715200  # 200MB
   ```

3. **Enable Whisper model caching**:
   ```bash
   WHISPER_MODEL=base
   WHISPER_DEVICE=cpu
   WHISPER_COMPUTE_TYPE=int8
   ```

---

## Related Documentation

- [API Reference](API_REFERENCE.md) - Complete API endpoint documentation
- [Code Examples](CODE_EXAMPLES.md) - Practical code examples
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions
- [CONFIG_GUIDE.md](../CONFIG_GUIDE.md) - Configuration guide