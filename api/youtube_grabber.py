#!/usr/bin/env python3
"""
YouTube Subtitle Grabber (using yt-dlp)

Features:
- Download subtitles from YouTube videos
- Support multiple languages
- Auto-merge subtitles into Markdown format
- Support all yt-dlp features

Usage:
    python youtube_grabber.py --url "https://youtu.be/VIDEO_ID" --output output.md
    python youtube_grabber.py --url "URL" --lang zh-Hant,en --output output.md
"""

import argparse
import subprocess
import json
import sys
import os
from pathlib import Path
from datetime import datetime


def get_video_info(url, verbose=False):
    """Get video information (excluding subtitles)"""
    if verbose:
        print(f"[{datetime.now().isoformat()}] Getting video info: {url}")
    
    cmd = [
        'yt-dlp',
        '--dump-json',
        '--no-download',
        url
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        if verbose:
            print(f"❌ Error: {result.stderr}")
        return None
    
    return json.loads(result.stdout)


def list_available_subtitles(url, verbose=False):
    """List available subtitle languages"""
    if verbose:
        print(f"[{datetime.now().isoformat()}] Checking available subtitles: {url}")
    
    cmd = [
        'yt-dlp',
        '--list-subs',
        '--no-download',
        url
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        if verbose:
            print(f"❌ Error: {result.stderr}")
        return []
    
    # Parse output
    subtitles = []
    for line in result.stdout.split('\n'):
        if 'Available subtitles' in line or 'Automatic captions' in line:
            continue
        if line.strip():
            subtitles.append(line.strip())
    
    return subtitles


def download_subtitles(url, output_path, languages=None, verbose=False):
    """
    Download subtitles and convert to Markdown
    
    Args:
        url: YouTube URL
        output_path: Output file path
        languages: Language list (default: ['zh-Hant', 'zh-Hans', 'en'])
        verbose: Verbose output
    """
    
    if languages is None:
        languages = ['zh-Hant', 'zh-Hans', 'en', 'zh-TW', 'zh-CN']
    
    if verbose:
        print(f"[{datetime.now().isoformat()}] Starting subtitle download")
        print(f"  URL: {url}")
        print(f"  Language priority: {', '.join(languages)}")
        print(f"  Output: {output_path}")
    
    # Create temp directory
    temp_dir = Path(output_path).parent / '.temp_subs'
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # Download subtitles
        cmd = [
            'yt-dlp',
            '--write-auto-sub',  # Download auto-generated subtitles
            '--write-sub',
            '--sub-lang', ','.join(languages),
            '--skip-download',  # Don't download video
            '--sub-format', 'vtt',  # VTT format
            '--convert-subs', 'vtt',  # Convert subtitle format
            '-o', str(temp_dir / '%(title)s.%(ext)s'),
            '--no-check-certificate',  # Skip certificate check
            url
        ]
        
        if verbose:
            print(f"  Executing: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            if verbose:
                print(f"❌ Download failed: {result.stderr}")
            return False
        
        # Find downloaded subtitle files
        sub_files = list(temp_dir.glob('*.vtt'))
        
        if not sub_files:
            if verbose:
                print("❌ No subtitle files found")
            return False
        
        if verbose:
            print(f"✅ Found {len(sub_files)} subtitle file(s)")
            for f in sub_files:
                print(f"   - {f.name}")
        
        # Convert to Markdown
        convert_subs_to_markdown(sub_files, output_path, verbose)
        
        return True
        
    finally:
        # Clean up temp files
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def convert_vtt_to_text(vtt_content):
    """Convert VTT subtitles to plain text"""
    lines = vtt_content.split('\n')
    text_lines = []
    
    for line in lines:
        # Skip VTT header and timestamps
        if line.startswith('WEBVTT'):
            continue
        if '-->' in line:
            continue
        if line.strip().isdigit():
            continue
        if line.startswith('NOTE'):
            continue
        if line.strip():
            text_lines.append(line.strip())
    
    return '\n'.join(text_lines)


def convert_subs_to_markdown(sub_files, output_path, verbose=False):
    """Convert VTT subtitle files to Markdown"""
    
    markdown_content = []
    markdown_content.append("# YouTube Subtitles\n")
    
    for sub_file in sorted(sub_files):
        # Extract language from filename
        lang = sub_file.stem.split('.')[-1] if '.' in sub_file.stem else 'unknown'
        
        with open(sub_file, 'r', encoding='utf-8') as f:
            vtt_content = f.read()
        
        # Convert to text
        text_content = convert_vtt_to_text(vtt_content)
        
        # Add to Markdown
        markdown_content.append(f"## Language: {lang}\n")
        markdown_content.append(text_content)
        markdown_content.append("\n---\n")
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(markdown_content))
    
    if verbose:
        print(f"✅ Written: {output_path}")
        print(f"   Total lines: {len(markdown_content)}")


def main():
    parser = argparse.ArgumentParser(
        description='YouTube Subtitle Grabber (using yt-dlp)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Basic usage (auto-select language)
  python youtube_grabber.py --url "https://youtu.be/VIDEO_ID" --output output.md
  
  # Specify language
  python youtube_grabber.py --url "URL" --lang zh-Hant,en --output output.md
  
  # Verbose output
  python youtube_grabber.py --url "URL" --output output.md --verbose
  
  # List available subtitles
  python youtube_grabber.py --url "URL" --list-subs
        """
    )
    
    parser.add_argument(
        '--url', '-u',
        required=True,
        help='YouTube video URL'
    )
    
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='Output Markdown file path'
    )
    
    parser.add_argument(
        '--lang', '-l',
        default='zh-Hant,zh-Hans,en',
        help='Subtitle languages (comma-separated, default: zh-Hant,zh-Hans,en)'
    )
    
    parser.add_argument(
        '--list-subs',
        action='store_true',
        help='Only list available subtitles, do not download'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Parse language list
    languages = [lang.strip() for lang in args.lang.split(',')]
    
    if args.list_subs:
        # Only list subtitles
        subs = list_available_subtitles(args.url, args.verbose)
        if subs:
            print("Available subtitles:")
            for sub in subs:
                print(f"  - {sub}")
        else:
            print("❌ No available subtitles found or error occurred")
            sys.exit(1)
    else:
        # Download subtitles
        success = download_subtitles(
            args.url,
            args.output,
            languages,
            args.verbose
        )
        
        if success:
            print(f"\n✅ Subtitle download successful!")
            print(f"   Output file: {args.output}")
            
            # Show statistics
            with open(args.output, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"   Character count: {len(content)}")
            print(f"   Line count: {content.count(chr(10)) + 1}")
        else:
            print("\n❌ Subtitle download failed")
            sys.exit(1)


if __name__ == "__main__":
    main()
