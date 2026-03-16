#!/usr/bin/env python3
"""
自動監控輸入目錄並轉換文件為 Markdown

功能：
- 監控 /app/input 目錄
- 當有新文件時自動轉換
- 轉換完成後輸出到 /app/output
- 支持移動/刪除原始文件（可選）
- 支持錯誤處理和重試
"""

import os
import sys
import time
import shutil
from pathlib import Path
from datetime import datetime
from markitdown import MarkItDown

# 配置
INPUT_DIR = os.getenv("AUTO_INPUT_DIR", "/app/input")
OUTPUT_DIR = os.getenv("AUTO_OUTPUT_DIR", "/app/output")
ENABLE_PLUGINS = os.getenv("AUTO_ENABLE_PLUGINS", "true").lower() == "true"
OCR_LANG = os.getenv("AUTO_OCR_LANG", "chi_tra+eng")
MOVE_SOURCE = os.getenv("AUTO_MOVE_SOURCE", "false").lower() == "true"
POLL_INTERVAL = int(os.getenv("AUTO_POLL_INTERVAL", "5"))
MAX_RETRIES = int(os.getenv("AUTO_MAX_RETRIES", "3"))
RETRY_BASE_DELAY = int(os.getenv("AUTO_RETRY_BASE_DELAY", "2"))
RETRY_MAX_DELAY = int(os.getenv("AUTO_RETRY_MAX_DELAY", "60"))
TEMP_DIR = os.getenv("AUTO_TEMP_DIR", "/app/temp")

try:
    from api.constants import SUPPORTED_EXTENSIONS
except ImportError:
    from constants import SUPPORTED_EXTENSIONS

# 初始化 MarkItDown
print(f"[{datetime.now().isoformat()}] 初始化 MarkItDown...")
md = MarkItDown(enable_plugins=ENABLE_PLUGINS)
print(f"[{datetime.now().isoformat()}] 監控服務啟動")
print(f"  - 輸入目錄：{INPUT_DIR}")
print(f"  - 輸出目錄：{OUTPUT_DIR}")
print(f"  - 啟用插件：{ENABLE_PLUGINS}")
print(f"  - OCR 語言：{OCR_LANG}")
print(f"  - 移動源文件：{MOVE_SOURCE}")
print(f"  - 監控間隔：{POLL_INTERVAL}秒")
print("-" * 50)


def get_supported_files(directory):
    """獲取目錄中所有支援的文件"""
    files = []
    dir_path = Path(directory)
    
    if not dir_path.exists():
        return files
    
    for file_path in dir_path.iterdir():
        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext in SUPPORTED_EXTENSIONS and not file_path.name.startswith('.'):
                files.append(file_path)
    
    return files


def convert_file(file_path):
    """轉換單一文件"""
    file_path = Path(file_path)
    output_path = Path(OUTPUT_DIR) / f"{file_path.stem}.md"
    
    print(f"[{datetime.now().isoformat()}] 開始轉換：{file_path.name}")
    
    try:
        # 執行轉換
        result = md.convert(str(file_path))
        
        # 寫入輸出文件
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result.text_content)
        
        print(f"[{datetime.now().isoformat()}] ✓ 轉換成功：{output_path.name}")
        
        # 如果需要移動源文件
        if MOVE_SOURCE:
            archive_dir = Path(INPUT_DIR) / ".processed"
            archive_dir.mkdir(exist_ok=True)
            shutil.move(str(file_path), str(archive_dir / file_path.name))
            print(f"[{datetime.now().isoformat()}]   已移動源文件到：{archive_dir}")
        
        return True
        
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] ✗ 轉換失敗：{str(e)}")
        return False


def convert_file_with_retry(file_path, max_retries=MAX_RETRIES):
    """轉換文件，指數退避重試"""
    for attempt in range(max_retries):
        try:
            return convert_file(file_path)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
                print(f"[{datetime.now().isoformat()}] ⚠️ 轉換失敗，{wait_time}秒後重試 ({attempt+1}/{max_retries}): {str(e)}")
                time.sleep(wait_time)
            else:
                print(f"[{datetime.now().isoformat()}] ✗ 重試次數用盡：{str(e)}")
                
                # 移動到失敗目錄
                failed_dir = Path(TEMP_DIR) / ".failed"
                failed_dir.mkdir(parents=True, exist_ok=True)
                
                # 移動文件
                shutil.move(str(file_path), str(failed_dir / file_path.name))
                
                # 寫入錯誤文件
                import json
                error_file = failed_dir / f"{file_path.name}.error"
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write(json.dumps({
                        "timestamp": datetime.now().isoformat(),
                        "error": str(e),
                        "retries": max_retries,
                        "file": str(file_path.name)
                    }, indent=2, ensure_ascii=False))
                
                print(f"[{datetime.now().isoformat()}] ✗ 文件已移至失敗目錄：{file_path.name}")
                return False
    return False


def main():
    """主循環"""
    # 確保目錄存在
    Path(INPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    # 處理現有文件（啟動時）
    print(f"[{datetime.now().isoformat()}] 掃描現有文件...")
    existing_files = get_supported_files(INPUT_DIR)
    
    if existing_files:
        print(f"  找到 {len(existing_files)}個文件")
        for file_path in existing_files:
            convert_file_with_retry(file_path)
    else:
        print("  沒有現有文件")
    
    print("-" * 50)
    print(f"[{datetime.now().isoformat()}] 開始監控（按 Ctrl+C 停止）...")
    
    # 監控循環
    processed_files = set()
    
    try:
        while True:
            # 獲取當前文件列表
            current_files = get_supported_files(INPUT_DIR)
            
            # 找出新文件
            new_files = [f for f in current_files if str(f) not in processed_files]
            
            if new_files:
                print(f"\n[{datetime.now().isoformat()}] 發現 {len(new_files)}個新文件")
                
                for file_path in new_files:
                    success = convert_file_with_retry(file_path)
                    
                    if success:
                        processed_files.add(str(file_path))
                    else:
                        # 轉換失敗，從列表中移除（下次重試）
                        processed_files.discard(str(file_path))
            
            # 等待下一次檢查
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().isoformat()}] 監控服務已停止")
        sys.exit(0)


if __name__ == "__main__":
    main()
