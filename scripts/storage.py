#!/usr/bin/env python3
"""
Storage query script for MarkItDown.

Usage:
    python scripts/storage.py
    python scripts/storage.py --json
"""

import argparse
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

TEMP_DIR = os.getenv("TEMP_DIR", "/tmp")

def get_storage_info():
    """Get detailed storage information."""
    info = {
        "total_bytes": 0,
        "total_mb": 0,
        "breakdown": {}
    }
    
    youtube_bytes = 0
    youtube_files = 0
    for f in Path(TEMP_DIR).glob("*.mp3"):
        if f.is_file():
            youtube_bytes += f.stat().st_size
            youtube_files += 1
    
    info["breakdown"]["youtube_audio"] = {
        "bytes": youtube_bytes,
        "mb": round(youtube_bytes / 1024 / 1024, 2),
        "files": youtube_files
    }
    
    ocr_bytes = 0
    ocr_files = 0
    for f in Path(TEMP_DIR).glob("page_*.png"):
        if f.is_file():
            ocr_bytes += f.stat().st_size
            ocr_files += 1
    
    info["breakdown"]["ocr_temp"] = {
        "bytes": ocr_bytes,
        "mb": round(ocr_bytes / 1024 / 1024, 2),
        "files": ocr_files
    }
    
    upload_bytes = 0
    upload_files = 0
    for f in Path(TEMP_DIR).glob("temp_*"):
        if f.is_file():
            upload_bytes += f.stat().st_size
            upload_files += 1
    
    info["breakdown"]["uploads"] = {
        "bytes": upload_bytes,
        "mb": round(upload_bytes / 1024 / 1024, 2),
        "files": upload_files
    }
    
    failed_bytes = 0
    failed_files = 0
    failed_dir = Path(TEMP_DIR) / ".failed"
    if failed_dir.exists():
        for f in failed_dir.iterdir():
            if f.is_file() and not f.name.endswith(".error"):
                failed_bytes += f.stat().st_size
                failed_files += 1
    
    info["breakdown"]["failed"] = {
        "bytes": failed_bytes,
        "mb": round(failed_bytes / 1024 / 1024, 2),
        "files": failed_files
    }
    
    info["total_bytes"] = youtube_bytes + ocr_bytes + upload_bytes + failed_bytes
    info["total_mb"] = round(info["total_bytes"] / 1024 / 1024, 2)
    
    return info

def main():
    parser = argparse.ArgumentParser(
        description='Query MarkItDown storage usage'
    )
    
    parser.add_argument(
        '--json', '-j',
        action='store_true',
        help='Output in JSON format'
    )
    
    args = parser.parse_args()
    
    info = get_storage_info()
    
    if args.json:
        print(json.dumps(info, indent=2))
    else:
        print("\n=== MarkItDown Storage Usage ===\n")
        
        for category, data in info["breakdown"].items():
            print(f"{category}:")
            print(f"  Files: {data['files']}")
            print(f"  Size:  {data['mb']:.2f} MB")
            print()
        
        print(f"Total: {info['total_mb']:.2f} MB ({info['total_bytes']} bytes)")

if __name__ == "__main__":
    main()
