.PHONY: install dev test lint format build up down logs clean

# 安裝依賴
install:
	uv sync

# 安裝開發依賴
dev:
	uv sync --all-extras

# 運行測試
test:
	uv run pytest -v --cov=api --cov-report=term-missing

# 代碼檢查
lint:
	uv run ruff check api tests
	uv run mypy api

# 格式化代碼
format:
	uv run ruff format api tests
	uv run ruff check --fix api tests

# Docker 構建
build:
	docker compose build

# Docker 啟動
up:
	docker compose up -d

# Docker 停止
down:
	docker compose down

# 查看日誌
logs:
	docker compose logs -f

# 清理
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov 2>/dev/null || true