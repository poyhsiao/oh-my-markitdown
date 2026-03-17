# MarkItDown API 配置指南 📝

> **基於：** [microsoft/markitdown](https://github.com/microsoft/markitdown)  
> **Original Project:** [microsoft/markitdown](https://github.com/microsoft/markitdown)

本指南幫助你快速配置 MarkItDown API 環境變數。

**[🇹🇼 繁體中文版](CONFIG_GUIDE_ZH_TW.md)** | **[🇺🇸 English](CONFIG_GUIDE_EN.md)** *(Coming Soon)*

---

## 🚀 快速開始（3 步驟）

### 步驟 1：複製配置範例

```bash
cd /Users/kimhsiao/git/kimhsiao/oh-my-markitdown
cp .env.example .env
```

### 步驟 2：編輯配置

```bash
# 使用 nano 編輯器
nano .env

# 或使用 vim
vim .env

# 或使用 VS Code
code .env
```

### 步驟 3：重啟服務

```bash
# 重啟使配置生效
docker compose restart

# 或完全重啟
docker compose down
docker compose up -d
```

---

## 📋 必須配置項目

### ✅ 基本使用（新手推薦）

只需確認以下兩項即可開始使用：

```bash
# 1. API 端口（預設 51083，如需修改請確保端口未被佔用）
API_PORT=51083

# 2. 預設 OCR 語言（根據你的主要文件類型調整）
# 繁體中文文件（推薦）
DEFAULT_OCR_LANG=chi_tra+eng

# 或簡體中文文件
# DEFAULT_OCR_LANG=chi_sim+eng

# 或日文文件
# DEFAULT_OCR_LANG=jpn+eng
```

---

## 🔧 常見場景配置

### 場景 1：更改 API 端口

如果 51083 端口被佔用，或你想使用其他端口：

```bash
# .env 文件
API_PORT=8080

# 重啟服務
docker compose restart

# 測試
curl http://localhost:8080/health
```

**常用端口：**
- `51083`（預設）
- `8080`（常見替代）
- `3000`（開發常用）
- `80`（HTTP 預設，需要 root 權限）

---

### 場景 2：主要處理簡體中文文件

如果你的文件主要是簡體中文：

```bash
# .env 文件
DEFAULT_OCR_LANG=chi_sim+eng

# 重啟服務
docker compose restart
```

---

### 場景 3：處理多語言混合文件

如果文件包含多種語言（如繁中 + 英文 + 日文）：

```bash
# .env 文件
DEFAULT_OCR_LANG=chi_tra+eng+jpn

# 重啟服務
docker compose restart
```

**語言組合範例：**
- `chi_tra+eng` - 繁體中文 + 英文（預設）
- `chi_sim+eng` - 簡體中文 + 英文
- `chi_tra+jpn+kor+eng` - 東北亞多語言
- `chi_tra+tha+vie+eng` - 東南亞多語言
- `chi_tra+chi_sim+eng+jpn+kor+tha+vie` - 完整亞洲語言（7 種）

---

### 場景 4：上傳大文件（>50MB）

如果需要處理大於 50MB 的文件：

```bash
# .env 文件
MAX_UPLOAD_SIZE=104857600  # 100MB

# 建議同時增加記憶體限制
MEMORY_LIMIT=4G

# 重啟服務
docker compose restart
```

**大小換算：**
- 10MB = `10485760`
- 50MB = `52428800`（預設）
- 100MB = `104857600`
- 500MB = `524288000`
- 1GB = `1073741824`

---

### 場景 5：使用 OpenAI 高品質 OCR

如果需要更高品質的 OCR（特別是複雜文件或低品質掃描）：

```bash
# .env 文件
OPENAI_API_KEY=sk-proj-your-api-key-here
OPENAI_MODEL=gpt-4o

# 重啟服務
docker compose restart

# 驗證配置
curl http://localhost:51083/config
```

**獲取 OpenAI API Key：**
1. 訪問 https://platform.openai.com/api-keys
2. 登入/註冊 OpenAI 帳號
3. 點擊 "Create new secret key"
4. 複製 API Key 到 `.env` 文件

**費用提示：**
- 使用 OpenAI 視覺模型會產生 API 費用
- 參考價格：https://openai.com/api/pricing/
- 建議先測試少量文件

---

### 場景 6：高性能需求（批量處理）

如果需要批量處理大量文件：

```bash
# .env 文件
MAX_UPLOAD_SIZE=524288000  # 500MB
MEMORY_LIMIT=4G
CPU_LIMIT=4.0
API_WORKERS=4

# 重啟服務
docker compose restart
```

**建議配置：**
| 文件數量 | MEMORY_LIMIT | CPU_LIMIT | API_WORKERS |
|----------|--------------|-----------|-------------|
| < 100/天 | 2G | 2.0 | 1-2 |
| 100-1000/天 | 4G | 4.0 | 2-4 |
| > 1000/天 | 8G | 8.0 | 4-8 |

---

### 場景 7：開發/調試環境

如果在開發或調試問題：

```bash
# .env 文件
API_DEBUG=true

# 重啟服務
docker compose restart
```

**效果：**
- API 會返回詳細錯誤信息
- 日誌會包含更多調試信息
- **注意：** 生產環境請設為 `false`

---

### 場景 8：生產環境配置

如果部署到生產環境：

```bash
# .env 文件
# 關閉調試模式
API_DEBUG=false

# 調整日誌配置
LOG_MAX_SIZE=50m
LOG_MAX_FILE=5

# 健康檢查
HEALTHCHECK_INTERVAL=30s
HEALTHCHECK_TIMEOUT=10s
HEALTHCHECK_RETRIES=3

# 資源限制（根據伺服器配置調整）
MEMORY_LIMIT=4G
CPU_LIMIT=4.0

# 重啟服務
docker compose restart
```

---

## 🎯 OCR 語言選擇指南

### 根據地區選擇

| 地區 | 推薦配置 |
|------|----------|
| 台灣 | `chi_tra+eng` |
| 香港 | `chi_tra+eng` |
| 中國大陸 | `chi_sim+eng` |
| 日本 | `jpn+eng` |
| 韓國 | `kor+eng` |
| 泰國 | `tha+eng` |
| 越南 | `vie+eng` |
| 新加坡/馬來西亞 | `chi_tra+chi_sim+eng` |

### 根據文件類型選擇

| 文件類型 | 推薦配置 |
|----------|----------|
| 學術論文（繁中） | `chi_tra+eng` |
| 商業文件（簡中） | `chi_sim+eng` |
| 技術文檔（日文） | `jpn+eng` |
| 多語言手冊 | `chi_tra+chi_sim+eng+jpn+kor` |
| 東南亞文件 | `chi_tra+tha+vie+eng` |

---

## ❓ 常見問題

### Q1: 修改 .env 後服務沒有變化？

**A:** 需要重啟服務才能生效：

```bash
docker compose restart
```

### Q2: 如何確認配置是否生效？

**A:** 使用 `/config` 端點檢查：

```bash
curl http://localhost:51083/config
```

### Q3: 端口被佔用怎麼辦？

**A:** 更改 `API_PORT` 為其他端口：

```bash
API_PORT=8080
```

### Q4: OCR 品質不佳怎麼辦？

**A:** 嘗試以下方法：
1. 增加語言組合（如 `chi_tra+eng+jpn`）
2. 使用 OpenAI 高品質 OCR（配置 `OPENAI_API_KEY`）
3. 提高原始文件掃描品質

### Q5: 如何恢復預設配置？

**A:** 重新複製範例文件：

```bash
cp .env.example .env
docker compose restart
```

---

## 📚 相關文件

- `.env.example` - 配置範例（含詳細註解）
- `.env` - 實際配置文件（請勿提交到 Git）
- `README.md` - 完整使用說明
- `docker-compose.yml` - Docker Compose 配置

---

## 🔗 外部資源

- [MarkItDown GitHub](https://github.com/microsoft/markitdown)
- [Tesseract OCR 文檔](https://tesseract-ocr.github.io/)
- [OpenAI API 文檔](https://platform.openai.com/docs)

---

**最後更新：** 2026-03-13  
**版本：** 1.1.0
