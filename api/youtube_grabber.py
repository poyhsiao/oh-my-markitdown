#!/usr/bin/env python3
"""
YouTube 字幕抓取工具（使用 yt-dlp）

功能：
- 從 YouTube 影片抓取字幕
- 支持多語言
- 自動合併字幕為 Markdown 格式
- 支持 yt-dlp 的所有功能

使用方式：
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
    """獲取影片資訊（不包含字幕）"""
    if verbose:
        print(f"[{datetime.now().isoformat()}] 獲取影片資訊：{url}")
    
    cmd = [
        'yt-dlp',
        '--dump-json',
        '--no-download',
        url
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        if verbose:
            print(f"❌ 錯誤：{result.stderr}")
        return None
    
    return json.loads(result.stdout)


def list_available_subtitles(url, verbose=False):
    """列出可用的字幕語言"""
    if verbose:
        print(f"[{datetime.now().isoformat()}] 檢查可用字幕：{url}")
    
    cmd = [
        'yt-dlp',
        '--list-subs',
        '--no-download',
        url
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        if verbose:
            print(f"❌ 錯誤：{result.stderr}")
        return []
    
    # 解析輸出
    subtitles = []
    for line in result.stdout.split('\n'):
        if 'Available subtitles' in line or 'Automatic captions' in line:
            continue
        if line.strip():
            subtitles.append(line.strip())
    
    return subtitles


def download_subtitles(url, output_path, languages=None, verbose=False):
    """
    下載字幕並轉換為 Markdown
    
    參數：
        url: YouTube URL
        output_path: 輸出文件路徑
        languages: 語言列表（預設：['zh-Hant', 'zh-Hans', 'en']）
        verbose: 詳細輸出
    """
    
    if languages is None:
        languages = ['zh-Hant', 'zh-Hans', 'en', 'zh-TW', 'zh-CN']
    
    if verbose:
        print(f"[{datetime.now().isoformat()}] 開始下載字幕")
        print(f"  URL: {url}")
        print(f"  語言優先順序：{', '.join(languages)}")
        print(f"  輸出：{output_path}")
    
    # 創建臨時目錄
    temp_dir = Path(output_path).parent / '.temp_subs'
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # 下載字幕
        cmd = [
            'yt-dlp',
            '--write-auto-sub',  # 下載自動生成的字幕
            '--write-sub',
            '--sub-lang', ','.join(languages),
            '--skip-download',  # 不下載視頻
            '--sub-format', 'vtt',  # VTT 格式
            '--convert-subs', 'vtt',  # 轉換字幕格式
            '-o', str(temp_dir / '%(title)s.%(ext)s'),
            '--no-check-certificate',  # 跳過證書檢查
            url
        ]
        
        if verbose:
            print(f"  執行：{' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            if verbose:
                print(f"❌ 下載失敗：{result.stderr}")
            return False
        
        # 查找下載的字幕文件
        sub_files = list(temp_dir.glob('*.vtt'))
        
        if not sub_files:
            if verbose:
                print("❌ 未找到字幕文件")
            return False
        
        if verbose:
            print(f"✅ 找到 {len(sub_files)} 個字幕文件")
            for f in sub_files:
                print(f"   - {f.name}")
        
        # 轉換為 Markdown
        convert_subs_to_markdown(sub_files, output_path, verbose)
        
        return True
        
    finally:
        # 清理臨時文件
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def convert_vtt_to_text(vtt_content):
    """將 VTT 字幕轉換為純文字"""
    lines = vtt_content.split('\n')
    text_lines = []
    
    for line in lines:
        # 跳過 VTT 頭部和時間軸
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
    """將 VTT 字幕文件轉換為 Markdown"""
    
    markdown_content = []
    markdown_content.append("# YouTube 字幕\n")
    
    for sub_file in sorted(sub_files):
        # 從文件名提取語言
        lang = sub_file.stem.split('.')[-1] if '.' in sub_file.stem else 'unknown'
        
        with open(sub_file, 'r', encoding='utf-8') as f:
            vtt_content = f.read()
        
        # 轉換為文字
        text_content = convert_vtt_to_text(vtt_content)
        
        # 添加到 Markdown
        markdown_content.append(f"## 語言：{lang}\n")
        markdown_content.append(text_content)
        markdown_content.append("\n---\n")
    
    # 寫入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(markdown_content))
    
    if verbose:
        print(f"✅ 已寫入：{output_path}")
        print(f"   總行數：{len(markdown_content)}")


def main():
    parser = argparse.ArgumentParser(
        description='YouTube 字幕抓取工具（使用 yt-dlp）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例：

  # 基本使用（自動選擇語言）
  python youtube_grabber.py --url "https://youtu.be/VIDEO_ID" --output output.md
  
  # 指定語言
  python youtube_grabber.py --url "URL" --lang zh-Hant,en --output output.md
  
  # 詳細輸出
  python youtube_grabber.py --url "URL" --output output.md --verbose
  
  # 列出可用字幕
  python youtube_grabber.py --url "URL" --list-subs
        """
    )
    
    parser.add_argument(
        '--url', '-u',
        required=True,
        help='YouTube 影片 URL'
    )
    
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='輸出 Markdown 文件路徑'
    )
    
    parser.add_argument(
        '--lang', '-l',
        default='zh-Hant,zh-Hans,en',
        help='字幕語言（逗號分隔，預設：zh-Hant,zh-Hans,en）'
    )
    
    parser.add_argument(
        '--list-subs',
        action='store_true',
        help='僅列出可用字幕，不下載'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='詳細輸出'
    )
    
    args = parser.parse_args()
    
    # 解析語言列表
    languages = [lang.strip() for lang in args.lang.split(',')]
    
    if args.list_subs:
        # 僅列出字幕
        subs = list_available_subtitles(args.url, args.verbose)
        if subs:
            print("可用字幕：")
            for sub in subs:
                print(f"  - {sub}")
        else:
            print("❌ 未找到可用字幕或發生錯誤")
            sys.exit(1)
    else:
        # 下載字幕
        success = download_subtitles(
            args.url,
            args.output,
            languages,
            args.verbose
        )
        
        if success:
            print(f"\n✅ 字幕下載成功！")
            print(f"   輸出文件：{args.output}")
            
            # 顯示統計
            with open(args.output, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"   字元數：{len(content)}")
            print(f"   行數：{content.count(chr(10)) + 1}")
        else:
            print("\n❌ 字幕下載失敗")
            sys.exit(1)


if __name__ == "__main__":
    main()
