#!/usr/bin/env python3
"""
MarkItDown 命令行工具

功能：
- 轉換本地文件為 Markdown
- YouTube 視頻轉錄
- 視頻文件轉錄
- 音頻文件轉錄
- URL 處理
- 緩存清理
- 隊列狀態查詢
- 配置顯示
- 健康檢查

使用方式：
    ./cli.py convert <file>
    ./cli.py youtube <url>
    ./cli.py video <file>
    ./cli.py audio <file>
    ./cli.py url <url>
    ./cli.py cleanup
    ./cli.py queue
    ./cli.py config
    ./cli.py health
"""

import argparse
import sys
import os
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional
import requests

# Import constants
import sys
from pathlib import Path

# Add parent directory to path for imports when running as script
sys.path.insert(0, str(Path(__file__).parent))

from api.constants import SUPPORTED_EXTENSIONS
from markitdown import MarkItDown


# API Configuration
API_URL = os.getenv('API_URL', 'http://localhost:51083')


def get_markitdown(enable_plugins=True, ocr_lang='chi_tra+eng'):
    """初始化 MarkItDown"""
    return MarkItDown(enable_plugins=enable_plugins)


def convert_file(input_path, output_path, enable_plugins=True, ocr_lang='chi_tra+eng', verbose=False):
    """轉換單一文件"""
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    if verbose:
        print(f"[{datetime.now().isoformat()}] 開始轉換：{input_path.name}")
    
    try:
        # 初始化
        md = get_markitdown(enable_plugins=enable_plugins, ocr_lang=ocr_lang)
        
        # 執行轉換
        result = md.convert(str(input_path))
        
        # 確保輸出目錄存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 寫入輸出文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result.text_content)
        
        if verbose:
            print(f"[{datetime.now().isoformat()}] ✓ 轉換成功：{output_path}")
        
        return True
        
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] ✗ 轉換失敗：{str(e)}", file=sys.stderr)
        return False


def convert_url(url, output_path, verbose=False):
    """從 URL 轉換"""
    output_path = Path(output_path)
    
    if verbose:
        print(f"[{datetime.now().isoformat()}] 開始抓取並轉換：{url}")
    
    try:
        # 初始化
        md = get_markitdown(enable_plugins=False)
        
        # 執行轉換
        result = md.convert(url)
        
        # 確保輸出目錄存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 寫入輸出文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result.text_content)
        
        if verbose:
            print(f"[{datetime.now().isoformat()}] ✓ 轉換成功：{output_path}")
        
        return True
        
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] ✗ 轉換失敗：{str(e)}", file=sys.stderr)
        return False


def cmd_convert(args):
    """文件轉換命令"""
    input_path = Path(args.file)
    
    # 確定輸出路徑
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}.md"
    
    # 轉換文件
    success = convert_file(
        input_path,
        output_path,
        enable_plugins=args.enable_ocr,
        ocr_lang=args.ocr_lang,
        verbose=args.verbose
    )
    
    sys.exit(0 if success else 1)


def cmd_youtube(args):
    """YouTube 轉錄命令"""
    url = args.url
    
    # 構建 API 請求
    api_url = f"{API_URL}/api/v1/convert/youtube"
    params = {
        'url': url,
        'language': args.language,
        'model_size': args.model,
        'return_format': args.format,
        'include_timestamps': args.include_timestamps,
        'include_metadata': True
    }
    
    if args.verbose:
        print(f"[{datetime.now().isoformat()}] 開始轉錄 YouTube 視頻：{url}")
    
    try:
        response = requests.post(api_url, params=params, timeout=600)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('success'):
            print(f"✗ 轉錄失敗：{data.get('error', {}).get('message', '未知錯誤')}", file=sys.stderr)
            sys.exit(1)
        
        # 確定輸出路徑
        if args.output:
            output_path = Path(args.output)
        else:
            # 從 URL 提取文件名
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            if parsed.hostname == 'www.youtube.com' or parsed.hostname == 'youtube.com':
                query = parse_qs(parsed.query)
                video_id = query.get('v', ['unknown'])[0]
                output_name = f"youtube_{video_id}"
            else:
                output_name = "youtube_transcript"
            output_path = Path(f"{output_name}.{args.format}")
        
        # 寫入文件
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if args.format == 'json':
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            content = data.get('data', {}).get('formats', {}).get(args.format, '')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        if args.verbose:
            print(f"[{datetime.now().isoformat()}] ✓ 轉錄成功：{output_path}")
        
        sys.exit(0)
        
    except requests.exceptions.RequestException as e:
        print(f"✗ API 請求失敗：{str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ 轉錄失敗：{str(e)}", file=sys.stderr)
        sys.exit(1)


def cmd_video(args):
    """視頻文件轉錄命令"""
    video_path = Path(args.file)
    
    if args.verbose:
        print(f"[{datetime.now().isoformat()}] 開始處理視頻文件：{video_path.name}")
    
    # 使用 ffmpeg 提取音頻
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
        temp_audio_path = temp_audio.name
    
    try:
        # 提取音頻
        if args.verbose:
            print(f"[{datetime.now().isoformat()}] 提取音頻...")
        
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',
            '-acodec', 'libmp3lame',
            '-q:a', '2',
            '-y',
            temp_audio_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"✗ 音頻提取失敗：{result.stderr}", file=sys.stderr)
            sys.exit(1)
        
        if args.verbose:
            print(f"[{datetime.now().isoformat()}] 音頻提取成功，開始轉錄...")
        
        # 調用音頻轉錄 API
        api_url = f"{API_URL}/api/v1/convert/audio"
        
        with open(temp_audio_path, 'rb') as audio_file:
            files = {'file': audio_file}
            params = {
                'language': args.language,
                'model_size': args.model,
                'return_format': args.format,
                'include_timestamps': args.include_timestamps
            }
            
            response = requests.post(api_url, files=files, params=params, timeout=600)
            response.raise_for_status()
        
        data = response.json()
        
        if not data.get('success'):
            print(f"✗ 轉錄失敗：{data.get('error', {}).get('message', '未知錯誤')}", file=sys.stderr)
            sys.exit(1)
        
        # 確定輸出路徑
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = video_path.parent / f"{video_path.stem}.{args.format}"
        
        # 寫入文件
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if args.format == 'json':
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            content = data.get('data', {}).get('formats', {}).get(args.format, '')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        if args.verbose:
            print(f"[{datetime.now().isoformat()}] ✓ 轉錄成功：{output_path}")
        
        sys.exit(0)
        
    except requests.exceptions.RequestException as e:
        print(f"✗ API 請求失敗：{str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ 轉錄失敗：{str(e)}", file=sys.stderr)
        sys.exit(1)
    finally:
        # 清理臨時音頻文件
        if os.path.exists(temp_audio_path):
            os.unlink(temp_audio_path)


def cmd_audio(args):
    """音頻文件轉錄命令"""
    audio_path = Path(args.file)
    
    if args.verbose:
        print(f"[{datetime.now().isoformat()}] 開始轉錄音頻文件：{audio_path.name}")
    
    try:
        # 調用音頻轉錄 API
        api_url = f"{API_URL}/api/v1/convert/audio"
        
        with open(audio_path, 'rb') as audio_file:
            files = {'file': audio_file}
            params = {
                'language': args.language,
                'model_size': args.model,
                'return_format': args.format,
                'include_timestamps': args.include_timestamps
            }
            
            response = requests.post(api_url, files=files, params=params, timeout=600)
            response.raise_for_status()
        
        data = response.json()
        
        if not data.get('success'):
            print(f"✗ 轉錄失敗：{data.get('error', {}).get('message', '未知錯誤')}", file=sys.stderr)
            sys.exit(1)
        
        # 確定輸出路徑
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = audio_path.parent / f"{audio_path.stem}.{args.format}"
        
        # 寫入文件
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if args.format == 'json':
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            content = data.get('data', {}).get('formats', {}).get(args.format, '')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        if args.verbose:
            print(f"[{datetime.now().isoformat()}] ✓ 轉錄成功：{output_path}")
        
        sys.exit(0)
        
    except requests.exceptions.RequestException as e:
        print(f"✗ API 請求失敗：{str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ 轉錄失敗：{str(e)}", file=sys.stderr)
        sys.exit(1)


def cmd_url(args):
    """URL 處理命令"""
    url = args.url
    
    if args.verbose:
        print(f"[{datetime.now().isoformat()}] 開始處理 URL：{url}")
    
    try:
        # 調用 URL 統一入口 API
        api_url = f"{API_URL}/api/v1/convert/url"
        params = {
            'url': url,
            'type_hint': args.type,
            'language': args.language,
            'model_size': args.model,
            'output_formats': args.formats,
            'include_timestamps': args.include_timestamps
        }
        
        response = requests.post(api_url, params=params, timeout=600)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('success'):
            print(f"✗ 處理失敗：{data.get('error', {}).get('message', '未知錯誤')}", file=sys.stderr)
            sys.exit(1)
        
        # 確定輸出路徑
        if args.output:
            output_path = Path(args.output)
        else:
            # 從 URL 提取文件名
            from urllib.parse import urlparse
            parsed = urlparse(url)
            output_name = Path(parsed.path).stem or 'output'
            output_path = Path(f"{output_name}.md")
        
        # 寫入文件
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 獲取主要格式（通常是 markdown）
        formats = data.get('data', {}).get('formats', {})
        content = formats.get('markdown', formats.get('srt', ''))
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if args.verbose:
            print(f"[{datetime.now().isoformat()}] ✓ 處理成功：{output_path}")
        
        sys.exit(0)
        
    except requests.exceptions.RequestException as e:
        print(f"✗ API 請求失敗：{str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ 處理失敗：{str(e)}", file=sys.stderr)
        sys.exit(1)


def cmd_cleanup(args):
    """緩存清理命令"""
    api_url = f"{API_URL}/api/v1/admin/cleanup"
    params = {
        'targets': args.target,
        'dry_run': not args.execute
    }
    
    try:
        response = requests.post(api_url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('success'):
            print(f"✗ 清理失敗：{data.get('error', {}).get('message', '未知錯誤')}", file=sys.stderr)
            sys.exit(1)
        
        cleaned = data.get('data', {}).get('cleaned', {})
        dry_run = data.get('data', {}).get('dry_run', True)
        
        print("清理預覽 (dry-run)" if dry_run else "清理執行")
        print("=" * 50)
        print(f"目標：{args.target}")
        print()
        
        # 顯示臨時文件
        temp_files = cleaned.get('temp_files', {})
        if temp_files:
            print("臨時文件：")
            for file_info in temp_files.get('files', []):
                print(f"  {file_info}")
            print(f"  總計：{temp_files.get('count', 0)} 個文件，{temp_files.get('size_mb', 0):.1f} MB")
            print()
        
        # 顯示 Whisper 緩存
        whisper_cache = cleaned.get('whisper_cache', {})
        if whisper_cache:
            print("Whisper 緩存：")
            for model in whisper_cache.get('models', []):
                print(f"  - {model}")
            print(f"  總計：{whisper_cache.get('count', 0)} 個模型，{whisper_cache.get('size_mb', 0):.1f} MB")
            print()
        
        total_freed = data.get('data', {}).get('total_freed_mb', 0)
        print(f"總計釋放：{total_freed:.1f} MB")
        
        if dry_run:
            print()
            print("使用 --execute 執行刪除。")
        
        sys.exit(0)
        
    except requests.exceptions.RequestException as e:
        print(f"✗ API 請求失敗：{str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ 清理失敗：{str(e)}", file=sys.stderr)
        sys.exit(1)


def cmd_queue(args):
    """隊列狀態命令"""
    api_url = f"{API_URL}/api/v1/admin/queue"
    
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('success'):
            print(f"✗ 查詢失敗：{data.get('error', {}).get('message', '未知錯誤')}", file=sys.stderr)
            sys.exit(1)
        
        queue_data = data.get('data', {})
        
        print("隊列狀態")
        print("=" * 50)
        print(f"當前處理中：{queue_data.get('current_processing', 0)}/{queue_data.get('max_concurrent', 0)}")
        print(f"隊列長度：{queue_data.get('queue_length', 0)}")
        print()
        
        # 顯示處理中的請求
        queue = queue_data.get('queue', [])
        processing = [q for q in queue if q.get('status') == 'processing']
        if processing:
            print("處理中：")
            for item in processing:
                print(f"  - {item.get('request_id')}: {item.get('type')} (處理中)")
            print()
        
        # 顯示排隊中的請求
        queued = [q for q in queue if q.get('status') == 'queued']
        if queued:
            print("排隊中：")
            for i, item in enumerate(queued, 1):
                print(f"  {i}. {item.get('request_id')}: {item.get('type')}")
        
        sys.exit(0)
        
    except requests.exceptions.RequestException as e:
        print(f"✗ API 請求失敗：{str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ 查詢失敗：{str(e)}", file=sys.stderr)
        sys.exit(1)


def cmd_config(args):
    """配置顯示命令"""
    api_url = f"{API_URL}/api/v1/admin/config"
    
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('success'):
            print(f"✗ 查詢失敗：{data.get('error', {}).get('message', '未知錯誤')}", file=sys.stderr)
            sys.exit(1)
        
        config = data.get('data', {})
        
        print("配置")
        print("=" * 50)
        print()
        
        # API 配置
        api = config.get('api', {})
        print("API:")
        print(f"  版本：{api.get('version', 'N/A')}")
        print(f"  端口：{api.get('port', 'N/A')}")
        print(f"  調試模式：{api.get('debug', False)}")
        print(f"  最大上傳大小：{api.get('max_upload_size_mb', 0)} MB")
        print(f"  上傳超時：{api.get('upload_timeout_minutes', 0)} 分鐘")
        print(f"  最大並發請求：{api.get('max_concurrent_requests', 0)}")
        print()
        
        # OCR 配置
        ocr = config.get('ocr', {})
        print("OCR:")
        print(f"  啟用：{ocr.get('enabled', False)}")
        print(f"  默認語言：{ocr.get('default_language', 'N/A')}")
        print(f"  OpenAI 啟用：{ocr.get('openai_enabled', False)}")
        print()
        
        # Whisper 配置
        whisper = config.get('whisper', {})
        print("Whisper:")
        print(f"  模型：{whisper.get('model', 'N/A')}")
        print(f"  設備：{whisper.get('device', 'N/A')}")
        print(f"  計算類型：{whisper.get('compute_type', 'N/A')}")
        print()
        
        # 清理配置
        cleanup = config.get('cleanup', {})
        print("清理:")
        print(f"  臨時文件閾值：{cleanup.get('temp_threshold_hours', 0)} 小時")
        print(f"  自動清理：{cleanup.get('auto_cleanup_enabled', False)}")
        print()
        
        # 管理配置
        admin = config.get('admin', {})
        print("管理:")
        print(f"  IP 限制：{admin.get('ip_restriction_enabled', False)}")
        allowed_ips = admin.get('allowed_ips', [])
        if allowed_ips:
            print(f"  允許的 IP：{', '.join(allowed_ips)}")
        else:
            print(f"  允許的 IP：(全部)")
        
        sys.exit(0)
        
    except requests.exceptions.RequestException as e:
        print(f"✗ API 請求失敗：{str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ 查詢失敗：{str(e)}", file=sys.stderr)
        sys.exit(1)


def cmd_health(args):
    """健康檢查命令"""
    api_url = f"{API_URL}/health"
    
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') == 'ok':
            print("健康檢查：OK")
            print(f"API 版本：{data.get('version', 'N/A')}")
            print(f"運行時間：{data.get('uptime', 'N/A')}")
            print(f"Whisper 模型：{data.get('whisper_model', 'N/A')}")
            sys.exit(0)
        else:
            print("健康檢查：失敗", file=sys.stderr)
            sys.exit(1)
        
    except requests.exceptions.RequestException as e:
        print(f"✗ API 請求失敗：{str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ 健康檢查失敗：{str(e)}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='MarkItDown 命令行工具 - 文件轉換與語音轉錄',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例：

  # 文件轉換
  ./cli.py convert document.pdf
  ./cli.py convert document.pdf --output result.md
  ./cli.py convert scanned.pdf --enable-ocr --ocr-lang chi_tra+eng

  # YouTube 轉錄
  ./cli.py youtube "https://youtube.com/watch?v=xxx"
  ./cli.py youtube <url> --language en --model small

  # 視頻轉錄
  ./cli.py video recording.mp4
  ./cli.py video recording.mp4 --language zh

  # 音頻轉錄
  ./cli.py audio podcast.mp3
  ./cli.py audio podcast.mp3 --model medium

  # URL 處理
  ./cli.py url "https://youtube.com/watch?v=xxx"
  ./cli.py url <url> --type youtube

  # 緩存清理
  ./cli.py cleanup --target temp
  ./cli.py cleanup --target temp --execute

  # 隊列狀態
  ./cli.py queue

  # 配置顯示
  ./cli.py config

  # 健康檢查
  ./cli.py health
        """
    )
    
    # 創建子解析器
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    subparsers.required = True
    
    # convert 命令
    convert_parser = subparsers.add_parser('convert', help='文件轉換')
    convert_parser.add_argument('file', help='輸入文件路徑')
    convert_parser.add_argument('--output', '-o', help='輸出文件路徑')
    convert_parser.add_argument('--enable-ocr', action='store_true', help='啟用 OCR')
    convert_parser.add_argument('--ocr-lang', default='chi_tra+eng', help='OCR 語言（預設：chi_tra+eng）')
    convert_parser.add_argument('--format', choices=['markdown', 'json'], default='markdown', help='輸出格式')
    convert_parser.add_argument('--verbose', '-v', action='store_true', help='詳細輸出')
    convert_parser.set_defaults(func=cmd_convert)
    
    # youtube 命令
    youtube_parser = subparsers.add_parser('youtube', help='YouTube 轉錄')
    youtube_parser.add_argument('url', help='YouTube 視頻 URL')
    youtube_parser.add_argument('--language', '-l', default='zh', help='語言代碼（預設：zh）')
    youtube_parser.add_argument('--model', '-m', choices=['tiny', 'base', 'small', 'medium', 'large'], default='base', help='Whisper 模型大小（預設：base）')
    youtube_parser.add_argument('--formats', '-f', default='markdown', help='輸出格式（逗號分隔）')
    youtube_parser.add_argument('--include-timestamps', action='store_true', help='包含時間戳')
    youtube_parser.add_argument('--output', '-o', help='輸出文件路徑')
    youtube_parser.add_argument('--format', choices=['markdown', 'json'], default='markdown', help='輸出格式')
    youtube_parser.add_argument('--verbose', '-v', action='store_true', help='詳細輸出')
    youtube_parser.set_defaults(func=cmd_youtube)
    
    # video 命令
    video_parser = subparsers.add_parser('video', help='視頻文件轉錄')
    video_parser.add_argument('file', help='視頻文件路徑')
    video_parser.add_argument('--language', '-l', default='zh', help='語言代碼（預設：zh）')
    video_parser.add_argument('--model', '-m', choices=['tiny', 'base', 'small', 'medium', 'large'], default='base', help='Whisper 模型大小（預設：base）')
    video_parser.add_argument('--formats', '-f', default='markdown', help='輸出格式（逗號分隔）')
    video_parser.add_argument('--include-timestamps', action='store_true', help='包含時間戳')
    video_parser.add_argument('--output', '-o', help='輸出文件路徑')
    video_parser.add_argument('--format', choices=['markdown', 'json'], default='markdown', help='輸出格式')
    video_parser.add_argument('--verbose', '-v', action='store_true', help='詳細輸出')
    video_parser.set_defaults(func=cmd_video)
    
    # audio 命令
    audio_parser = subparsers.add_parser('audio', help='音頻文件轉錄')
    audio_parser.add_argument('file', help='音頻文件路徑')
    audio_parser.add_argument('--language', '-l', default='zh', help='語言代碼（預設：zh）')
    audio_parser.add_argument('--model', '-m', choices=['tiny', 'base', 'small', 'medium', 'large'], default='base', help='Whisper 模型大小（預設：base）')
    audio_parser.add_argument('--formats', '-f', default='markdown', help='輸出格式（逗號分隔）')
    audio_parser.add_argument('--include-timestamps', action='store_true', help='包含時間戳')
    audio_parser.add_argument('--output', '-o', help='輸出文件路徑')
    audio_parser.add_argument('--format', choices=['markdown', 'json'], default='markdown', help='輸出格式')
    audio_parser.add_argument('--verbose', '-v', action='store_true', help='詳細輸出')
    audio_parser.set_defaults(func=cmd_audio)
    
    # url 命令
    url_parser = subparsers.add_parser('url', help='URL 處理')
    url_parser.add_argument('url', help='URL 地址')
    url_parser.add_argument('--type', '-t', choices=['auto', 'youtube', 'document', 'audio', 'video', 'webpage'], default='auto', help='類型提示（預設：auto）')
    url_parser.add_argument('--language', '-l', default='auto', help='語言代碼（預設：auto）')
    url_parser.add_argument('--model', '-m', choices=['tiny', 'base', 'small', 'medium', 'large'], default='base', help='Whisper 模型大小（預設：base）')
    url_parser.add_argument('--formats', '-f', default='markdown', help='輸出格式（逗號分隔）')
    url_parser.add_argument('--include-timestamps', action='store_true', help='包含時間戳')
    url_parser.add_argument('--output', '-o', help='輸出文件路徑')
    url_parser.add_argument('--verbose', '-v', action='store_true', help='詳細輸出')
    url_parser.set_defaults(func=cmd_url)
    
    # cleanup 命令
    cleanup_parser = subparsers.add_parser('cleanup', help='緩存清理')
    cleanup_parser.add_argument('--target', '-t', choices=['temp', 'whisper', 'all'], default='temp', help='清理目標（預設：temp）')
    cleanup_parser.add_argument('--dry-run', action='store_true', help='預覽模式（預設）')
    cleanup_parser.add_argument('--execute', action='store_true', help='執行刪除')
    cleanup_parser.set_defaults(func=cmd_cleanup)
    
    # queue 命令
    queue_parser = subparsers.add_parser('queue', help='隊列狀態')
    queue_parser.set_defaults(func=cmd_queue)
    
    # config 命令
    config_parser = subparsers.add_parser('config', help='配置顯示')
    config_parser.set_defaults(func=cmd_config)
    
    # health 命令
    health_parser = subparsers.add_parser('health', help='健康檢查')
    health_parser.set_defaults(func=cmd_health)
    
    # 解析參數
    args = parser.parse_args()
    
    # 執行對應的命令
    args.func(args)


if __name__ == "__main__":
    main()
