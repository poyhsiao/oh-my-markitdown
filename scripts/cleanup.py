#!/usr/bin/env python3
"""
Cleanup script for MarkItDown temporary files.

Usage:
    python scripts/cleanup.py --types youtube,ocr,uploads,failed,models,all
    python scripts/cleanup.py --dry-run
    python scripts/cleanup.py --force
"""

import argparse
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.constants import CLEANUP_TYPES

TEMP_DIR = os.getenv("TEMP_DIR", "/tmp")

def get_storage_info():
    """Get storage information."""
    info = {
        "youtube_audio": {"files": 0, "bytes": 0},
        "ocr_temp": {"files": 0, "bytes": 0},
        "uploads": {"files": 0, "bytes": 0},
        "failed": {"files": 0, "bytes": 0},
    }
    
    for f in Path(TEMP_DIR).glob("*.mp3"):
        if f.is_file():
            info["youtube_audio"]["files"] += 1
            info["youtube_audio"]["bytes"] += f.stat().st_size
    
    for f in Path(TEMP_DIR).glob("page_*.png"):
        if f.is_file():
            info["ocr_temp"]["files"] += 1
            info["ocr_temp"]["bytes"] += f.stat().st_size
    
    for f in Path(TEMP_DIR).glob("temp_*"):
        if f.is_file():
            info["uploads"]["files"] += 1
            info["uploads"]["bytes"] += f.stat().st_size
    
    failed_dir = Path(TEMP_DIR) / ".failed"
    if failed_dir.exists():
        for f in failed_dir.iterdir():
            if f.is_file() and not f.name.endswith(".error"):
                info["failed"]["files"] += 1
                info["failed"]["bytes"] += f.stat().st_size
    
    return info

def cleanup(types, dry_run=False):
    """Perform cleanup."""
    if "all" in types:
        types = ["youtube", "ocr", "uploads", "failed", "models"]
    
    result = {
        "cleaned": {},
        "total_freed_bytes": 0
    }
    
    if "youtube" in types:
        count = 0
        freed = 0
        for f in Path(TEMP_DIR).glob("*.mp3"):
            if f.is_file():
                freed += f.stat().st_size
                if not dry_run:
                    f.unlink()
                count += 1
        result["cleaned"]["youtube_audio"] = {"files": count, "bytes": freed}
        result["total_freed_bytes"] += freed
    
    if "ocr" in types:
        count = 0
        freed = 0
        for f in Path(TEMP_DIR).glob("page_*.png"):
            if f.is_file():
                freed += f.stat().st_size
                if not dry_run:
                    f.unlink()
                count += 1
        result["cleaned"]["ocr_temp"] = {"files": count, "bytes": freed}
        result["total_freed_bytes"] += freed
    
    if "uploads" in types:
        count = 0
        freed = 0
        for f in Path(TEMP_DIR).glob("temp_*"):
            if f.is_file():
                freed += f.stat().st_size
                if not dry_run:
                    f.unlink()
                count += 1
        result["cleaned"]["uploads"] = {"files": count, "bytes": freed}
        result["total_freed_bytes"] += freed
    
    if "failed" in types:
        count = 0
        freed = 0
        failed_dir = Path(TEMP_DIR) / ".failed"
        if failed_dir.exists():
            for f in failed_dir.iterdir():
                if f.is_file():
                    freed += f.stat().st_size
                    if not dry_run:
                        f.unlink()
                    count += 1
        result["cleaned"]["failed"] = {"files": count, "bytes": freed}
        result["total_freed_bytes"] += freed
    
    if "models" in types:
        result["cleaned"]["models"] = {
            "note": "Model cache can only be cleared via API"
        }
    
    return result

def main():
    parser = argparse.ArgumentParser(
        description='Cleanup MarkItDown temporary files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Preview what would be cleaned
    python scripts/cleanup.py --dry-run
    
    # Clean YouTube audio files
    python scripts/cleanup.py --types youtube --force
    
    # Clean all temporary files
    python scripts/cleanup.py --types all --force
    
    # Clean specific types
    python scripts/cleanup.py --types ocr,uploads --force
        """
    )
    
    parser.add_argument(
        '--types', '-t',
        nargs='+',
        default=['all'],
        choices=list(CLEANUP_TYPES.keys()),
        help='Types to clean (default: all)'
    )
    
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be cleaned without actually cleaning'
    )
    
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Actually perform cleanup (required for safety)'
    )
    
    parser.add_argument(
        '--json', '-j',
        action='store_true',
        help='Output in JSON format'
    )
    
    args = parser.parse_args()
    
    info = get_storage_info()
    
    if args.dry_run:
        print("DRY RUN - No files will be deleted\n")
        print("Would clean:")
        for type_name in args.types:
            if type_name == "all":
                for t in ["youtube_audio", "ocr_temp", "uploads", "failed"]:
                    print(f"  {t}: {info[t]['files']} files, {info[t]['bytes'] / 1024 / 1024:.2f} MB")
            else:
                type_key = type_name if type_name != "youtube" else "youtube_audio"
                if type_key in info:
                    print(f"  {type_key}: {info[type_key]['files']} files, {info[type_key]['bytes'] / 1024 / 1024:.2f} MB")
        
        print("\nUse --force to actually clean up files")
        return
    
    if not args.force:
        print("ERROR: --force is required to perform cleanup")
        print("Use --dry-run to preview what would be cleaned")
        sys.exit(1)
    
    result = cleanup(args.types)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Cleanup complete:")
        for key, value in result["cleaned"].items():
            if isinstance(value, dict) and "files" in value:
                print(f"  {key}: {value['files']} files, {value['bytes'] / 1024 / 1024:.2f} MB freed")
            else:
                print(f"  {key}: {value}")
        
        total_mb = result["total_freed_bytes"] / 1024 / 1024
        print(f"\nTotal freed: {total_mb:.2f} MB")

if __name__ == "__main__":
    main()
