#!/usr/bin/env python3
"""
Auto-monitor input directory and convert files to Markdown

Features:
- Monitor /app/input directory
- Auto-convert when new files are detected
- Output converted files to /app/output
- Support moving/deleting source files (optional)
- Support error handling and retry
"""

import os
import sys
import time
import shutil
from pathlib import Path
from datetime import datetime
from markitdown import MarkItDown

# Configuration
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

# Initialize MarkItDown
print(f"[{datetime.now().isoformat()}] Initializing MarkItDown...")
md = MarkItDown(enable_plugins=ENABLE_PLUGINS)
print(f"[{datetime.now().isoformat()}] Monitoring service started")
print(f"  - Input directory: {INPUT_DIR}")
print(f"  - Output directory: {OUTPUT_DIR}")
print(f"  - Plugins enabled: {ENABLE_PLUGINS}")
print(f"  - OCR language: {OCR_LANG}")
print(f"  - Move source files: {MOVE_SOURCE}")
print(f"  - Poll interval: {POLL_INTERVAL}s")
print("-" * 50)


def get_supported_files(directory):
    """Get all supported files in the directory"""
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
    """Convert a single file"""
    file_path = Path(file_path)
    output_path = Path(OUTPUT_DIR) / f"{file_path.stem}.md"
    
    print(f"[{datetime.now().isoformat()}] Starting conversion: {file_path.name}")
    
    try:
        # Execute conversion
        result = md.convert(str(file_path))
        
        # Write output file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result.text_content)
        
        print(f"[{datetime.now().isoformat()}] ✓ Conversion successful: {output_path.name}")
        
        # Move source file if required
        if MOVE_SOURCE:
            archive_dir = Path(INPUT_DIR) / ".processed"
            archive_dir.mkdir(exist_ok=True)
            shutil.move(str(file_path), str(archive_dir / file_path.name))
            print(f"[{datetime.now().isoformat()}]   Source file moved to: {archive_dir}")
        
        return True
        
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] ✗ Conversion failed: {str(e)}")
        return False


def convert_file_with_retry(file_path, max_retries=MAX_RETRIES):
    """Convert file with exponential backoff retry"""
    # Ensure file_path is a Path object
    file_path = Path(file_path) if isinstance(file_path, str) else file_path
    
    for attempt in range(max_retries):
        try:
            return convert_file(file_path)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
                print(f"[{datetime.now().isoformat()}] ⚠️ Conversion failed, retrying in {wait_time}s ({attempt+1}/{max_retries}): {str(e)}")
                time.sleep(wait_time)
            else:
                print(f"[{datetime.now().isoformat()}] ✗ Retry attempts exhausted: {str(e)}")
                
                # Move to failed directory
                failed_dir = Path(TEMP_DIR) / ".failed"
                failed_dir.mkdir(parents=True, exist_ok=True)
                
                # Move file
                shutil.move(str(file_path), str(failed_dir / file_path.name))
                
                # Write error file
                import json
                error_file = failed_dir / f"{file_path.name}.error"
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write(json.dumps({
                        "timestamp": datetime.now().isoformat(),
                        "error": str(e),
                        "retries": max_retries,
                        "file": str(file_path.name)
                    }, indent=2, ensure_ascii=False))
                
                print(f"[{datetime.now().isoformat()}] ✗ File moved to failed directory: {file_path.name}")
                return False
    return False


def main():
    """Main loop"""
    # Ensure directories exist
    Path(INPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    # Process existing files (on startup)
    print(f"[{datetime.now().isoformat()}] Scanning existing files...")
    existing_files = get_supported_files(INPUT_DIR)
    
    if existing_files:
        print(f"  Found {len(existing_files)} file(s)")
        for file_path in existing_files:
            convert_file_with_retry(file_path)
    else:
        print("  No existing files")
    
    print("-" * 50)
    print(f"[{datetime.now().isoformat()}] Starting monitoring (press Ctrl+C to stop)...")
    
    # Monitoring loop
    processed_files = set()
    
    try:
        while True:
            # Get current file list
            current_files = get_supported_files(INPUT_DIR)
            
            # Find new files
            new_files = [f for f in current_files if str(f) not in processed_files]
            
            if new_files:
                print(f"\n[{datetime.now().isoformat()}] Detected {len(new_files)} new file(s)")
                
                for file_path in new_files:
                    success = convert_file_with_retry(file_path)
                    
                    if success:
                        processed_files.add(str(file_path))
                    else:
                        # Conversion failed, remove from list (retry next time)
                        processed_files.discard(str(file_path))
            
            # Wait for next check
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().isoformat()}] Monitoring service stopped")
        sys.exit(0)


if __name__ == "__main__":
    main()
