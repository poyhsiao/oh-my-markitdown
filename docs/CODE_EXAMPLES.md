# Code Examples

Practical code examples for using MarkItDown API in Python, cURL, and Node.js.

## Table of Contents

- [Python](#python)
- [cURL](#curl)
- [Node.js](#nodejs)

---

## Python

### Basic Conversion

```python
import requests

with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:51083/convert',
        files={'file': f},
        params={'return_format': 'json'}
    )

data = response.json()
print(f"Filename: {data['filename']}")
print(f"Content length: {len(data['content'])}")
print(data['content'][:500])  # Preview first 500 chars
```

### OCR Conversion (Traditional Chinese)

```python
import requests

with open('scanned-doc.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:51083/convert',
        files={'file': f},
        data={
            'enable_plugins': 'true',
            'ocr_lang': 'chi_tra+eng',
            'return_format': 'markdown'
        }
    )

with open('output.md', 'w', encoding='utf-8') as f:
    f.write(response.text)

print("Traditional Chinese OCR conversion complete!")
```

### Multi-Language OCR (Northeast Asia)

```python
import requests

with open('mixed-asian-doc.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:51083/convert',
        files={'file': f},
        data={
            'enable_plugins': 'true',
            'ocr_lang': 'chi_tra+eng+jpn+kor',
            'return_format': 'json'
        }
    )

data = response.json()
print(f"Filename: {data['filename']}")
print(f"Content length: {len(data['content'])} chars")
```

### Southeast Asian Language OCR (Thai + Vietnamese)

```python
import requests

# Thai document
with open('thai-document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:51083/convert',
        files={'file': f},
        data={
            'enable_plugins': 'true',
            'ocr_lang': 'tha+eng',
            'return_format': 'markdown'
        }
    )

with open('thai-output.md', 'w', encoding='utf-8') as f:
    f.write(response.text)

print("Thai OCR conversion complete!")

# Vietnamese document
with open('vietnamese-document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:51083/convert',
        files={'file': f},
        data={
            'enable_plugins': 'true',
            'ocr_lang': 'vie+eng',
            'return_format': 'markdown'
        }
    )

with open('vietnamese-output.md', 'w', encoding='utf-8') as f:
    f.write(response.text)

print("Vietnamese OCR conversion complete!")
```

### Complete Asian Language Support (All 7 Languages)

```python
import requests

# All supported Asian languages
ocr_languages = [
    "chi_tra",  # Traditional Chinese
    "chi_sim",  # Simplified Chinese
    "eng",      # English
    "jpn",      # Japanese
    "kor",      # Korean
    "tha",      # Thai
    "vie",      # Vietnamese
]

# All languages combined (suitable for multi-language documents)
all_langs = "+".join(ocr_languages)
print(f"Using language combination: {all_langs}")

with open('multi-lang-asia.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:51083/convert',
        files={'file': f},
        data={
            'enable_plugins': 'true',
            'ocr_lang': all_langs,
            'return_format': 'json'
        }
    )

data = response.json()
print(f"Conversion successful! Content length: {len(data['content'])} chars")
```

### Batch Conversion

```python
import requests
from pathlib import Path

# Batch convert all PDFs in input/ directory
input_dir = Path('input')
output_dir = Path('output')
output_dir.mkdir(exist_ok=True)

for pdf_file in input_dir.glob('*.pdf'):
    print(f"Converting: {pdf_file.name}")
    
    with open(pdf_file, 'rb') as f:
        response = requests.post(
            'http://localhost:51083/convert',
            files={'file': f},
            data={
                'enable_plugins': 'true',
                'ocr_lang': 'chi_tra+eng'
            }
        )
    
    output_file = output_dir / f"{pdf_file.stem}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(response.text)
    
    print(f"✓ Complete: {output_file.name}")

print("\nBatch conversion complete!")
```

---

## cURL

### Basic Conversion

```bash
curl -X POST "http://localhost:51083/api/v1/convert" \
  -F "file=@document.pdf" \
  -o output.md
```

### OCR Conversion (Specify Language)

```bash
# Traditional Chinese
curl -X POST "http://localhost:51083/api/v1/convert" \
  -F "file=@scanned-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+eng" \
  -o output.md

# Simplified Chinese
curl -X POST "http://localhost:51083/api/v1/convert" \
  -F "file=@chinese-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_sim+eng" \
  -o output.md

# Japanese
curl -X POST "http://localhost:51083/api/v1/convert" \
  -F "file=@japanese-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=jpn+eng" \
  -o output.md

# Korean
curl -X POST "http://localhost:51083/api/v1/convert" \
  -F "file=@korean-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=kor+eng" \
  -o output.md

# Thai
curl -X POST "http://localhost:51083/api/v1/convert" \
  -F "file=@thai-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=tha+eng" \
  -o output.md

# Vietnamese
curl -X POST "http://localhost:51083/api/v1/convert" \
  -F "file=@vietnamese-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=vie+eng" \
  -o output.md
```

### Multi-Language Mix

```bash
# Northeast Asian multi-language
curl -X POST "http://localhost:51083/api/v1/convert" \
  -F "file=@northeast-asia-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+jpn+kor+eng" \
  -o output.md

# Southeast Asian multi-language
curl -X POST "http://localhost:51083/api/v1/convert" \
  -F "file=@southeast-asia-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+tha+vie+eng" \
  -o output.md

# Complete Asian languages (all 7)
curl -X POST "http://localhost:51083/api/v1/convert" \
  -F "file=@all-asia-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+chi_sim+eng+jpn+kor+tha+vie" \
  -o output.md
```

### Batch Conversion (Shell Script)

```bash
#!/bin/bash

# Batch convert all PDFs in input/ directory
for file in input/*.pdf; do
    filename=$(basename "$file" .pdf)
    echo "Converting: $filename.pdf"
    
    curl -X POST "http://localhost:51083/api/v1/convert" \
        -F "file=@$file" \
        -F "enable_plugins=true" \
        -F "ocr_lang=chi_tra+eng" \
        -o "output/${filename}.md"
    
    echo "✓ Complete: ${filename}.md"
done

echo "\nBatch conversion complete!"
```

---

## Node.js

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

// Basic conversion
const form = new FormData();
form.append('file', fs.createReadStream('document.pdf'));
form.append('return_format', 'json');

const response = await axios.post(
    'http://localhost:51083/convert',
    form,
    { headers: form.getHeaders() }
);

console.log('Conversion successful:', response.data.filename);
fs.writeFileSync('output.md', response.data.content);

// OCR conversion (Traditional Chinese)
const ocrForm = new FormData();
ocrForm.append('file', fs.createReadStream('scanned-doc.jpg'));
ocrForm.append('enable_plugins', 'true');
ocrForm.append('ocr_lang', 'chi_tra+eng');
ocrForm.append('return_format', 'markdown');

const ocrResponse = await axios.post(
    'http://localhost:51083/convert',
    ocrForm,
    { headers: ocrForm.getHeaders() }
);

fs.writeFileSync('output-ocr.md', ocrResponse.data);
console.log('OCR conversion complete!');
```

---

## YouTube Transcription Examples

### Python

```python
import requests

# Chinese transcription (auto-detect subtitles, fastest)
response = requests.post(
    'http://localhost:51083/api/v1/convert/youtube',
    params={
        'url': 'https://www.youtube.com/watch?v=VIDEO_ID',
        'language': 'zh',
        'model_size': 'base',
        'prefer_subtitles': True  # Use YouTube subtitles if available (2-5 seconds)
    }
)

with open('transcript.md', 'w', encoding='utf-8') as f:
    f.write(response.text)

# Force Whisper transcription (skip subtitle check)
response = requests.post(
    'http://localhost:51083/api/v1/convert/youtube',
    params={
        'url': 'https://www.youtube.com/watch?v=VIDEO_ID',
        'language': 'zh',
        'prefer_subtitles': False,  # Force Whisper transcription
        'fast_mode': True  # Enable optimizations for faster processing
    }
)

with open('transcript_whisper.md', 'w', encoding='utf-8') as f:
    f.write(response.text)
```

### cURL

```bash
# Chinese transcription (auto-detect subtitles)
curl -X POST "http://localhost:51083/api/v1/convert/youtube?url=https://www.youtube.com/watch?v=VIDEO_ID&language=zh" \
  -o transcript.md

# Force Whisper transcription with fast mode
curl -X POST "http://localhost:51083/api/v1/convert/youtube?url=https://www.youtube.com/watch?v=VIDEO_ID&prefer_subtitles=false&fast_mode=true" \
  -o transcript.md

# English transcription with JSON output
curl -X POST "http://localhost:51083/api/v1/convert/youtube?url=https://www.youtube.com/watch?v=VIDEO_ID&language=en&return_format=json" \
  -o response.json
```

---

## Audio Transcription Examples

### Python

```python
import requests

with open('audio.mp3', 'rb') as f:
    response = requests.post(
        'http://localhost:51083/api/v1/convert/audio',
        files={'file': f},
        params={'language': 'zh'}
    )

with open('transcript.md', 'w', encoding='utf-8') as f:
    f.write(response.text)
```

### cURL

```bash
curl -X POST "http://localhost:51083/api/v1/convert/audio?language=zh" \
  -F "file=@audio.mp3" \
  -o transcript.md
```

---

## Related Documentation

- [API Reference](API_REFERENCE.md) - Complete API endpoint documentation
- [Advanced Configuration](ADVANCED_CONFIG.md) - OpenAI, Azure, and Docker configuration
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions