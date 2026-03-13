# MarkItDown API Docker 🐳🚀

透過 HTTP API 將各種文件格式轉換為 Markdown！

## 📦 支援的文件格式

| 類型 | 格式 |
|------|------|
| **文件** | PDF、Word (DOCX/DOC)、PowerPoint (PPTX/PPT)、Excel (XLSX/XLS) |
| **網頁** | HTML、URL（含 YouTube） |
| **圖片** | JPG、PNG、GIF、WEBP、BMP、TIFF（含 EXIF + 多語言 OCR） |
| **音頻** | MP3、WAV、M4A、FLAC、OGG（含語音轉錄） |
| **資料** | CSV、JSON、XML |
| **其他** | ZIP、EPub、Outlook 郵件 |

## 🔤 OCR 多語言支援

| 語言代碼 | 語言 | 說明 |
|----------|------|------|
| `chi_tra` | 繁體中文 | 台灣、香港、澳門繁體字 |
| `chi_sim` | 簡體中文 | 中國大陸簡體字 |
| `eng` | 英文 | English |
| `jpn` | 日文 | 日本語（含漢字、平假名、片假名） |
| `kor` | 韓文 | 한국어（諺文） |

**組合使用：** 使用 `+` 符號組合多種語言，例如：
- `chi_tra+eng`（繁體中文 + 英文，預設）
- `chi_sim+eng`（簡體中文 + 英文）
- `chi_tra+jpn+kor+eng`（多語言混合）

## 🚀 快速開始

### 1. 建置並啟動服務

```bash
cd /Users/kimhsiao/git/kimhsiao/markitdown-kim

# 建置 Docker 映像
docker compose build

# 啟動服務
docker compose up -d

# 查看日誌
docker compose logs -f
```

服務將在 **http://localhost:51083** 啟動！

### 2. 測試服務

```bash
# 健康檢查
curl http://localhost:51083/health

# 查看支援格式
curl http://localhost:51083/formats
```

---

## 📡 API 使用說明

### API 端點

#### 1. `POST /convert` - 上傳文件並轉換

**請求：**
```bash
curl -X POST "http://localhost:51083/convert" \
  -F "file=@your-file.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+eng" \
  -F "return_format=markdown" \
  -o output.md
```

**參數：**
- `file` (必填): 要轉換的文件檔案
- `enable_plugins` (選填): 是否啟用插件（預設 `false`）
- `ocr_lang` (選填): OCR 語言代碼（預設 `chi_tra+eng`，支援 `chi_tra`, `chi_sim`, `eng`, `jpn`, `kor`，可用 `+` 組合）
- `return_format` (選填): `markdown` 或 `json`（預設 `markdown`）

**回傳格式：**

**Markdown（預設）：**
- Content-Type: `text/markdown`
- 直接回傳 Markdown 內容
- Headers 包含原始檔名和轉換時間

**JSON：**
```json
{
  "success": true,
  "filename": "document.pdf",
  "file_size": 123456,
  "conversion_time": "2026-03-13T14:30:00",
  "content": "# Markdown 內容...",
  "metadata": {
    "type": "pdf",
    "source": "file",
    "title": "文件標題",
    "author": "作者"
  }
}
```

---

#### 2. `POST /convert/url` - 從 URL 轉換

**請求：**
```bash
curl -X POST "http://localhost:51083/convert/url?url=https://example.com/article" \
  -o output.md
```

**參數：**
- `url` (必填): 網頁 URL 或 YouTube URL
- `return_format` (選填): `markdown` 或 `json`

---

#### 3. `GET /formats` - 查看支援格式

```bash
curl http://localhost:51083/formats
```

---

#### 4. `GET /health` - 健康檢查

```bash
curl http://localhost:51083/health
```

#### 5. `GET /ocr-languages` - 查看 OCR 語言支援

```bash
curl http://localhost:51083/ocr-languages
```

**回傳範例：**
```json
{
  "supported_languages": {
    "chi_sim": "簡體中文",
    "chi_tra": "繁體中文",
    "eng": "英文",
    "jpn": "日文",
    "kor": "韓文"
  },
  "default": "chi_tra+eng",
  "usage": "使用 + 符號組合多種語言，例如：chi_tra+eng+jpn",
  "examples": [
    {"code": "chi_tra", "name": "繁體中文"},
    {"code": "chi_sim", "name": "簡體中文"},
    {"code": "eng", "name": "英文"},
    {"code": "jpn", "name": "日文"},
    {"code": "kor", "name": "韓文"},
    {"code": "chi_tra+eng", "name": "繁體中文 + 英文（預設）"},
    {"code": "chi_sim+eng", "name": "簡體中文 + 英文"},
    {"code": "chi_tra+jpn+kor+eng", "name": "多語言混合"}
  ]
}
```

---

## 💻 程式碼範例

### Python

```python
import requests

# 上傳文件轉換
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:51083/convert',
        files={'file': f},
        data={'enable_plugins': 'false', 'return_format': 'markdown'}
    )

# 儲存結果
with open('output.md', 'w') as f:
    f.write(response.text)

print(f"轉換完成！狀態碼：{response.status_code}")
```

### Python（JSON 格式）

```python
import requests

with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:51083/convert',
        files={'file': f},
        params={'return_format': 'json'}
    )

data = response.json()
print(f"檔名：{data['filename']}")
print(f"內容長度：{len(data['content'])}")
print(data['content'][:500])  # 預覽前 500 字
```

### Python（OCR 轉換 - 繁體中文）

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

print("OCR 轉換完成！")
```

### Python（多語言 OCR）

```python
import requests

# 混合語言文件（繁中 + 英文 + 日文 + 韓文）
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
print(f"檔名：{data['filename']}")
print(f"內容長度：{len(data['content'])} 字元")
```

### cURL（批量轉換）

```bash
# 批量轉換 input/ 目錄下所有 PDF
for file in input/*.pdf; do
    filename=$(basename "$file" .pdf)
    curl -X POST "http://localhost:51083/convert" \
        -F "file=@$file" \
        -o "output/${filename}.md"
    echo "轉換完成：$filename.md"
done
```

### Node.js

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

const form = new FormData();
form.append('file', fs.createReadStream('document.pdf'));
form.append('return_format', 'json');

const response = await axios.post(
    'http://localhost:51083/convert',
    form,
    { headers: form.getHeaders() }
);

console.log('轉換成功:', response.data.filename);
fs.writeFileSync('output.md', response.data.content);
```

---

## 🔧 進階配置

### 啟用 OCR 插件

如需使用 OCR 功能（從圖片提取文字），可指定語言：

**繁體中文文件：**
```bash
curl -X POST "http://localhost:51083/convert" \
  -F "file=@scanned-document.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+eng" \
  -o output.md
```

**簡體中文文件：**
```bash
curl -X POST "http://localhost:51083/convert" \
  -F "file=@chinese-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_sim+eng" \
  -o output.md
```

**多語言混合（繁中 + 英文 + 日文）：**
```bash
curl -X POST "http://localhost:51083/convert" \
  -F "file=@mixed-lang.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+eng+jpn" \
  -o output.md
```

**韓文文件：**
```bash
curl -X POST "http://localhost:51083/convert" \
  -F "file=@korean-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=kor+eng" \
  -o output.md
```

**查看支援的 OCR 語言：**
```bash
curl http://localhost:51083/ocr-languages
```

### 使用 OpenAI 視覺模型（進階）

如需更高品質的 OCR，可使用 OpenAI 視覺模型：

**docker-compose.yml：**
```yaml
environment:
  - OPENAI_API_KEY=sk-your-key-here
```

**Python 範例：**
```python
from markitdown import MarkItDown
from openai import OpenAI

client = OpenAI()
md = MarkItDown(
    enable_plugins=True,
    llm_client=client,
    llm_model="gpt-4o"
)
result = md.convert("scanned-document.pdf")
print(result.text_content)
```

### 調整資源限制

編輯 `docker-compose.yml` 中的 `deploy.resources` 部分：

```yaml
deploy:
  resources:
    limits:
      memory: 4G    # 增加記憶體
      cpus: '4.0'   # 增加 CPU
```

### 持久化存儲

添加數據卷以保留轉換記錄：

```yaml
volumes:
  - ./data:/app/data
```

---

## 📊 API 互動文件

啟動服務後，訪問 **Swagger UI**：

```
http://localhost:51083/docs
```

或 **ReDoc**：

```
http://localhost:51083/redoc
```

---

## 🗑️ 停止與清理

```bash
# 停止服務
docker compose down

# 停止並刪除映像
docker compose down --rmi all

# 查看日誌
docker compose logs -f

# 重新啟動
docker compose restart
```

---

## 🔍 故障排除

### 容器無法啟動

```bash
# 查看日誌
docker compose logs markitdown-api

# 檢查端口是否被佔用
lsof -i :51083
```

### 轉換失敗

1. 檢查文件格式是否支援：`curl http://localhost:51083/formats`
2. 查看容器日誌：`docker compose logs -f`
3. 確認文件大小（建議 < 50MB）

### 記憶體不足

增加 `docker-compose.yml` 中的記憶體限制：

```yaml
deploy:
  resources:
    limits:
      memory: 4G
```

---

## 📄 授權

MarkItDown 由 Microsoft 開源，遵循 MIT 授權。

---

**建立者：** kimhsiao  
**日期：** 2026-03-13  
**API 端口：** 51083
