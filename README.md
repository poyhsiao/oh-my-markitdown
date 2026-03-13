# MarkItDown API Docker 🐳🚀

透過 HTTP API 將各種文件格式轉換為 Markdown！

## 📦 支援的文件格式

| 類型 | 格式 |
|------|------|
| **文件** | PDF、Word (DOCX/DOC)、PowerPoint (PPTX/PPT)、Excel (XLSX/XLS) |
| **網頁** | HTML、URL（含 YouTube） |
| **圖片** | JPG、PNG、GIF、WEBP、BMP、TIFF（含 EXIF + OCR） |
| **音頻** | MP3、WAV、M4A、FLAC、OGG（含語音轉錄） |
| **資料** | CSV、JSON、XML |
| **其他** | ZIP、EPub、Outlook 郵件 |

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
  -F "enable_plugins=false" \
  -F "return_format=markdown" \
  -o output.md
```

**參數：**
- `file` (必填): 要轉換的文件檔案
- `enable_plugins` (選填): 是否啟用插件（預設 `false`）
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

如需使用 OCR 功能（從圖片提取文字），需要設置 OpenAI API Key：

**docker-compose.yml：**
```yaml
environment:
  - OPENAI_API_KEY=sk-your-key-here
```

**API 請求：**
```bash
curl -X POST "http://localhost:51083/convert" \
  -F "file=@scanned-document.pdf" \
  -F "enable_plugins=true" \
  -o output.md
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
