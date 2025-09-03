"""
Enhanced PDF Report Generator
PDFレポート生成モジュール - 最適化版
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import tempfile
import subprocess
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import json

from models.article import Article
from utils.config import get_config
from .html_generator import HTMLReportGenerator

logger = logging.getLogger(__name__)


class PDFGenerationError(Exception):
    """PDF生成関連エラー"""
    pass


class OptimizedPDFReportGenerator:
    """最適化されたPDFレポート生成"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.html_generator = HTMLReportGenerator(config)
        
        # wkhtmltopdf設定
        self.wkhtmltopdf_path = self._find_wkhtmltopdf()
        
        # 最適化されたPDF生成オプション
        self.pdf_options = {
            # ページ設定
            'page-size': 'A4',
            'orientation': 'Portrait',
            'margin-top': '15mm',
            'margin-right': '10mm',
            'margin-bottom': '15mm',
            'margin-left': '10mm',
            
            # エンコーディング
            'encoding': 'UTF-8',
            
            # パフォーマンス最適化
            'enable-local-file-access': None,
            'disable-smart-shrinking': None,
            'print-media-type': None,
            'no-outline': None,
            'disable-javascript': None,  # JS無効化で高速化
            'lowquality': None,  # 低品質モードで高速化（本番では削除可能）
            
            # レンダリング最適化
            'dpi': '96',  # DPI設定
            'image-dpi': '96',
            'image-quality': '85',  # 画像品質（85%で十分）
            
            # タイムアウト設定
            'load-error-handling': 'ignore',
            'load-media-error-handling': 'ignore',
            
            # メモリ最適化
            'minimum-font-size': '8',
            
            # ヘッダー・フッター
            'header-spacing': '5',
            'footer-spacing': '5',
        }
        
        # 日本語フォント対応
        self._setup_japanese_fonts()
        
        # 出力ディレクトリ
        project_root = Path(__file__).parent.parent.parent
        default_reports_dir = project_root / 'data' / 'reports'
        self.output_dir = Path(self.config.get('paths.reports', 
                                             default=str(default_reports_dir)))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # パフォーマンス統計
        self.generation_stats = {
            'total_generated': 0,
            'successful': 0,
            'failed': 0,
            'average_time': 0.0,
            'last_generation': None
        }
        
        logger.info(f"Optimized PDF Generator initialized. wkhtmltopdf: {self.wkhtmltopdf_path}")
    
    def _setup_japanese_fonts(self):
        """日本語フォント設定"""
        # 日本語フォントの追加設定
        japanese_font_options = {
            'allow': '/usr/share/fonts/',  # Linuxフォントディレクトリ
        }
        
        # Windows環境の場合
        if os.name == 'nt':
            japanese_font_options['allow'] = 'C:/Windows/Fonts/'
        
        self.pdf_options.update(japanese_font_options)
    
    async def generate_daily_report_async(self, articles: List[Article], 
                                         report_date: datetime = None) -> Optional[str]:
        """非同期PDF生成（日次レポート）"""
        try:
            report_date = report_date or datetime.now()
            start_time = datetime.now()
            
            # HTML生成
            html_content = self.html_generator.generate_daily_report(articles, report_date)
            
            # HTMLの最適化
            html_content = self._optimize_html(html_content)
            
            # PDF出力パス
            date_str = report_date.strftime('%Y%m%d')
            pdf_filename = f"daily_news_report_{date_str}.pdf"
            pdf_path = self.output_dir / "daily" / pdf_filename
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 非同期PDF生成
            success = await self._generate_pdf_async(html_content, str(pdf_path))
            
            # 統計更新
            generation_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(success, generation_time)
            
            if success:
                logger.info(f"Daily PDF report generated in {generation_time:.2f}s: {pdf_path}")
                
                # ファイルサイズ最適化
                self._optimize_pdf_file(pdf_path)
                
                return str(pdf_path)
            else:
                logger.error("Failed to generate daily PDF report")
                return None
                
        except Exception as e:
            logger.error(f"Daily PDF report generation failed: {e}")
            self._update_stats(False, 0)
            return None
    
    def _optimize_html(self, html_content: str) -> str:
        """HTML最適化"""
        # 不要な空白削除
        import re
        
        # 複数の空白を単一に
        html_content = re.sub(r'\s+', ' ', html_content)
        
        # 改行の最適化
        html_content = re.sub(r'>\s+<', '><', html_content)
        
        # インラインCSS最適化
        html_content = self._optimize_inline_css(html_content)
        
        # 画像の最適化（base64エンコードされた画像を圧縮）
        html_content = self._optimize_images(html_content)
        
        return html_content
    
    def _optimize_inline_css(self, html_content: str) -> str:
        """インラインCSS最適化"""
        # CSSの圧縮
        import re
        
        # コメント削除
        html_content = re.sub(r'/\*.*?\*/', '', html_content, flags=re.DOTALL)
        
        # 不要な空白削除
        html_content = re.sub(r':\s+', ':', html_content)
        html_content = re.sub(r';\s+', ';', html_content)
        
        return html_content
    
    def _optimize_images(self, html_content: str) -> str:
        """画像最適化"""
        # base64画像の検出と最適化
        import re
        import base64
        from PIL import Image
        from io import BytesIO
        
        def optimize_base64_image(match):
            try:
                # base64データを取得
                base64_str = match.group(1)
                img_data = base64.b64decode(base64_str)
                
                # PILで画像を開く
                img = Image.open(BytesIO(img_data))
                
                # 画像サイズを最適化（最大幅800px）
                max_width = 800
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
                # 画像を圧縮
                output = BytesIO()
                img.save(output, format='JPEG', quality=85, optimize=True)
                
                # 新しいbase64文字列を生成
                new_base64 = base64.b64encode(output.getvalue()).decode()
                return f'data:image/jpeg;base64,{new_base64}'
                
            except Exception:
                # エラーの場合は元のデータを返す
                return match.group(0)
        
        # base64画像を検出して最適化
        pattern = r'data:image/[^;]+;base64,([^"\']+)'
        html_content = re.sub(pattern, optimize_base64_image, html_content)
        
        return html_content
    
    async def _generate_pdf_async(self, html_content: str, output_path: str) -> bool:
        """非同期PDF生成"""
        try:
            if not self.wkhtmltopdf_path:
                raise PDFGenerationError("wkhtmltopdf not found")
            
            # 一時HTMLファイル作成
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', 
                                           delete=False, encoding='utf-8') as temp_file:
                # HTMLヘッダーに日本語フォント指定を追加
                if '<head>' in html_content:
                    font_style = '''
                    <style>
                        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
                        body { font-family: 'Noto Sans JP', sans-serif; }
                    </style>
                    '''
                    html_content = html_content.replace('<head>', f'<head>{font_style}')
                
                temp_file.write(html_content)
                temp_html_path = temp_file.name
            
            try:
                # wkhtmltopdfコマンド構築
                cmd = [self.wkhtmltopdf_path]
                
                # オプション追加
                for option, value in self.pdf_options.items():
                    if value is None:
                        cmd.append(f'--{option}')
                    else:
                        cmd.extend([f'--{option}', str(value)])
                
                # 入力・出力ファイル指定
                cmd.extend([temp_html_path, output_path])
                
                logger.debug(f"Running command: {' '.join(cmd)}")
                
                # 非同期でPDF生成実行
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # タイムアウト付きで待機（60秒）
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), 
                        timeout=60
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                    raise PDFGenerationError("PDF generation timeout")
                
                if process.returncode == 0:
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        logger.debug(f"PDF successfully generated: {output_path}")
                        return True
                    else:
                        logger.error(f"PDF file was not created or is empty: {output_path}")
                        return False
                else:
                    logger.error(f"wkhtmltopdf failed with return code {process.returncode}")
                    if stderr:
                        logger.error(f"STDERR: {stderr.decode('utf-8', errors='ignore')}")
                    return False
                    
            finally:
                # 一時ファイル削除
                try:
                    os.unlink(temp_html_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_html_path}: {e}")
            
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            return False
    
    def _optimize_pdf_file(self, pdf_path: Path):
        """PDFファイル最適化"""
        try:
            # Ghostscriptを使用したPDF圧縮（利用可能な場合）
            if self._find_ghostscript():
                optimized_path = pdf_path.with_suffix('.optimized.pdf')
                
                gs_cmd = [
                    'gs',
                    '-sDEVICE=pdfwrite',
                    '-dCompatibilityLevel=1.4',
                    '-dPDFSETTINGS=/ebook',  # 電子書籍品質
                    '-dNOPAUSE',
                    '-dQUIET',
                    '-dBATCH',
                    f'-sOutputFile={optimized_path}',
                    str(pdf_path)
                ]
                
                result = subprocess.run(gs_cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and optimized_path.exists():
                    # 元のファイルと最適化版のサイズを比較
                    original_size = pdf_path.stat().st_size
                    optimized_size = optimized_path.stat().st_size
                    
                    if optimized_size < original_size * 0.9:  # 10%以上削減された場合
                        pdf_path.unlink()
                        optimized_path.rename(pdf_path)
                        logger.info(f"PDF optimized: {original_size} -> {optimized_size} bytes")
                    else:
                        optimized_path.unlink()
                        
        except Exception as e:
            logger.debug(f"PDF optimization skipped: {e}")
    
    def _find_ghostscript(self) -> bool:
        """Ghostscriptの存在確認"""
        try:
            result = subprocess.run(['which', 'gs'], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def _find_wkhtmltopdf(self) -> Optional[str]:
        """wkhtmltopdfのパスを探索（最適化版）"""
        
        # キャッシュされたパスを確認
        cached_path = self.config.get('pdf_generation.wkhtmltopdf_path')
        if cached_path and os.path.isfile(cached_path):
            return cached_path
        
        # システムコマンドで高速検索
        for cmd in ['which', 'where']:
            try:
                result = subprocess.run([cmd, 'wkhtmltopdf'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    path = result.stdout.strip().split('\n')[0]
                    if os.path.isfile(path):
                        # 見つかったパスをキャッシュ
                        self._cache_wkhtmltopdf_path(path)
                        return path
            except:
                continue
        
        # 一般的なパスを検索
        possible_paths = [
            '/usr/bin/wkhtmltopdf',
            '/usr/local/bin/wkhtmltopdf',
            '/opt/wkhtmltopdf/bin/wkhtmltopdf',
            'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe',
            'C:\\Program Files (x86)\\wkhtmltopdf\\bin\\wkhtmltopdf.exe',
            '/opt/homebrew/bin/wkhtmltopdf'
        ]
        
        for path in possible_paths:
            if os.path.isfile(path):
                self._cache_wkhtmltopdf_path(path)
                return path
        
        logger.warning("wkhtmltopdf not found. PDF generation will not be available.")
        return None
    
    def _cache_wkhtmltopdf_path(self, path: str):
        """wkhtmltopdfパスをキャッシュ"""
        try:
            # 設定ファイルに保存
            config_path = Path(__file__).parent.parent.parent / 'config' / 'pdf_settings.json'
            config_path.parent.mkdir(exist_ok=True)
            
            settings = {}
            if config_path.exists():
                with open(config_path, 'r') as f:
                    settings = json.load(f)
            
            settings['wkhtmltopdf_path'] = path
            
            with open(config_path, 'w') as f:
                json.dump(settings, f, indent=2)
                
        except Exception as e:
            logger.debug(f"Failed to cache wkhtmltopdf path: {e}")
    
    def _update_stats(self, success: bool, generation_time: float):
        """統計更新"""
        self.generation_stats['total_generated'] += 1
        
        if success:
            self.generation_stats['successful'] += 1
            
            # 平均時間更新
            current_avg = self.generation_stats['average_time']
            total = self.generation_stats['successful']
            self.generation_stats['average_time'] = (
                (current_avg * (total - 1) + generation_time) / total
            )
        else:
            self.generation_stats['failed'] += 1
        
        self.generation_stats['last_generation'] = datetime.now().isoformat()
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """生成統計取得"""
        stats = self.generation_stats.copy()
        
        if stats['total_generated'] > 0:
            stats['success_rate'] = (
                stats['successful'] / stats['total_generated'] * 100
            )
        else:
            stats['success_rate'] = 0
        
        return stats
    
    def test_pdf_generation(self) -> Dict[str, Any]:
        """PDF生成機能テスト（最適化版）"""
        try:
            if not self.wkhtmltopdf_path:
                return {
                    'success': False,
                    'error': 'wkhtmltopdf not found',
                    'suggestion': 'Please install wkhtmltopdf: sudo apt-get install wkhtmltopdf'
                }
            
            # テスト用HTML（最適化済み）
            test_html = '''<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8">
            <title>PDF Test</title><style>body{font-family:sans-serif;margin:40px;}
            h1{color:#007bff;}</style></head><body><h1>PDF生成テスト</h1>
            <p>このファイルはPDF生成機能のテストです。</p>
            <p>生成日時: ''' + datetime.now().strftime('%Y年%m月%d日 %H:%M:%S') + '''</p>
            </body></html>'''
            
            # テストPDF生成
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            test_pdf_path = self.output_dir / "test" / f"pdf_test_{timestamp}.pdf"
            test_pdf_path.parent.mkdir(exist_ok=True)
            
            # 同期版テスト（簡易版）
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                f.write(test_html)
                temp_path = f.name
            
            try:
                cmd = [self.wkhtmltopdf_path, '--quiet', temp_path, str(test_pdf_path)]
                result = subprocess.run(cmd, capture_output=True, timeout=10)
                
                if result.returncode == 0 and test_pdf_path.exists():
                    file_size = test_pdf_path.stat().st_size
                    return {
                        'success': True,
                        'pdf_path': str(test_pdf_path),
                        'file_size': file_size,
                        'wkhtmltopdf_path': self.wkhtmltopdf_path,
                        'message': 'PDF generation test successful'
                    }
                else:
                    return {
                        'success': False,
                        'error': f'Generation failed: {result.stderr.decode() if result.stderr else "Unknown error"}'
                    }
            finally:
                os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"PDF generation test failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# グローバルインスタンス
_optimized_pdf_generator = None


def get_optimized_pdf_generator() -> OptimizedPDFReportGenerator:
    """最適化PDFジェネレーターインスタンス取得"""
    global _optimized_pdf_generator
    if _optimized_pdf_generator is None:
        _optimized_pdf_generator = OptimizedPDFReportGenerator()
    return _optimized_pdf_generator