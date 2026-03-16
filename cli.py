#!/usr/bin/env python3
"""
MarkItDown 命令行工具

功能：
- 轉換本地文件為 Markdown
- 從 URL 抓取並轉換為 Markdown
- 自訂輸出位置
- 支持批量處理
- 支持多語言 OCR

使用方式：
    python cli.py input.pdf output.md
    python cli.py --url https://example.com output.md
    python cli.py *.pdf -o ./output/
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
from markitdown import MarkItDown

# Import constants
import sys
from pathlib import Path

# Add parent directory to path for imports when running as script
sys.path.insert(0, str(Path(__file__).parent))

from api.constants import SUPPORTED_EXTENSIONS


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


def main():
    parser = argparse.ArgumentParser(
        description='MarkItDown 命令行工具 - 轉換文件為 Markdown',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例：

  # 轉換單一文件
  python cli.py document.pdf output.md
  
  # 從 URL 轉換
  python cli.py --url https://example.com output.md
  
  # 批量轉換（指定輸出目錄）
  python cli.py *.pdf -o ./output/
  
  # 使用 OCR（繁體中文 + 英文）
  python cli.py scanned.pdf output.md --ocr-lang chi_tra+eng
  
  # 詳細輸出
  python cli.py document.pdf output.md --verbose
  
  # 輸出到 stdout
  python cli.py document.pdf --stdout
        """
    )
    
    # 輸入參數
    parser.add_argument(
        'input',
        nargs='*',
        help='輸入文件路徑（多個文件時使用空格分隔）'
    )
    
    parser.add_argument(
        '--url', '-u',
        help='從 URL 抓取並轉換'
    )
    
    # 輸出參數
    parser.add_argument(
        '--output', '-o',
        help='輸出目錄或文件路徑'
    )
    
    parser.add_argument(
        '--stdout',
        action='store_true',
        help='輸出到標準輸出（不寫入文件）'
    )
    
    # OCR 配置
    parser.add_argument(
        '--ocr-lang',
        default='chi_tra+eng',
        help='OCR 語言（預設：chi_tra+eng）'
    )
    
    parser.add_argument(
        '--no-plugins',
        action='store_true',
        help='禁用插件（包括 OCR）'
    )
    
    # 其他選項
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='詳細輸出'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='MarkItDown CLI 1.1.0'
    )
    
    args = parser.parse_args()
    
    # 驗證輸入
    if not args.input and not args.url:
        parser.print_help()
        print("\n錯誤：請提供輸入文件或 URL", file=sys.stderr)
        sys.exit(1)
    
    # 處理 URL 輸入
    if args.url:
        if args.stdout:
            # 輸出到 stdout
            md = get_markitdown(enable_plugins=not args.no_plugins)
            result = md.convert(args.url)
            print(result.text_content)
        else:
            # 輸出到文件
            if not args.output:
                # 自動生成輸出文件名
                from urllib.parse import urlparse
                parsed = urlparse(args.url)
                output_name = Path(parsed.path).stem or 'output'
                output_path = Path(f"{output_name}.md")
            else:
                output_path = Path(args.output)
                # 如果是目錄，自動生成文件名
                if output_path.is_dir():
                    from urllib.parse import urlparse
                    parsed = urlparse(args.url)
                    output_name = Path(parsed.path).stem or 'output'
                    output_path = output_path / f"{output_name}.md"
            
            success = convert_url(args.url, output_path, verbose=args.verbose)
            sys.exit(0 if success else 1)
    
    # 處理文件輸入
    if args.input:
        input_files = []
        
        # 展開 glob 模式（如 *.pdf）
        for pattern in args.input:
            matches = list(Path('.').glob(pattern))
            if matches:
                input_files.extend(matches)
            elif Path(pattern).exists():
                input_files.append(Path(pattern))
            else:
                print(f"警告：找不到文件 '{pattern}'", file=sys.stderr)
        
        if not input_files:
            print("錯誤：沒有找到匹配的輸入文件", file=sys.stderr)
            sys.exit(1)
        
        # 驗證文件類型
        valid_files = []
        for file_path in input_files:
            ext = file_path.suffix.lower()
            if ext in SUPPORTED_EXTENSIONS:
                valid_files.append(file_path)
            else:
                print(f"警告：跳過不支援的文件類型 '{file_path.name}' ({ext})", file=sys.stderr)
        
        if not valid_files:
            print("錯誤：沒有支援的文件格式", file=sys.stderr)
            sys.exit(1)
        
        # 處理輸出
        if args.stdout:
            # 輸出到 stdout（僅支持單一文件）
            if len(valid_files) > 1:
                print("錯誤：--stdout 僅支持單一文件輸入", file=sys.stderr)
                sys.exit(1)
            
            md = get_markitdown(enable_plugins=not args.no_plugins)
            result = md.convert(str(valid_files[0]))
            print(result.text_content)
        else:
            # 輸出到文件
            enable_plugins = not args.no_plugins
            success_count = 0
            
            for i, file_path in enumerate(valid_files):
                if args.output:
                    output_path = Path(args.output)
                    
                    # 如果是目錄，自動生成文件名
                    if output_path.is_dir() or args.output.endswith('/'):
                        output_path = output_path / f"{file_path.stem}.md"
                    elif len(valid_files) > 1:
                        # 批量處理時，如果輸出不是目錄，視為目錄
                        print(f"錯誤：批量處理時輸出必須是目錄", file=sys.stderr)
                        sys.exit(1)
                else:
                    # 自動生成輸出文件名（與輸入同目錄）
                    output_path = file_path.parent / f"{file_path.stem}.md"
                
                # 轉換文件
                success = convert_file(
                    file_path,
                    output_path,
                    enable_plugins=enable_plugins,
                    ocr_lang=args.ocr_lang,
                    verbose=args.verbose
                )
                
                if success:
                    success_count += 1
            
            # 總結
            total = len(valid_files)
            print(f"\n轉換完成：{success_count}/{total} 個文件成功")
            
            if success_count < total:
                sys.exit(1)


if __name__ == "__main__":
    main()
