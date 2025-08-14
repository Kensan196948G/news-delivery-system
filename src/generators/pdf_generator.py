"""
PDF Report Generator
PDFレポート生成モジュール - wkhtmltopdf使用
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os
import logging
import tempfile
import subprocess
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from models.article import Article
from utils.config import get_config
from .html_generator import HTMLReportGenerator

logger = logging.getLogger(__name__)


class PDFGenerationError(Exception):
    """PDF生成関連エラー"""
    pass


class PDFReportGenerator:
    """PDFレポート生成"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.html_generator = HTMLReportGenerator(config)
        
        # wkhtmltopdf設定
        self.wkhtmltopdf_path = self._find_wkhtmltopdf()
        
        # PDF生成オプション
        self.pdf_options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in', 
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': 'UTF-8',
            'no-outline': None,
            'enable-local-file-access': None,
            'print-media-type': None,
            'disable-smart-shrinking': None
        }
        
        # 出力ディレクトリ
        # プロジェクトルートからの相対パスで設定
        project_root = Path(__file__).parent.parent.parent
        default_reports_dir = project_root / 'data' / 'reports'
        self.output_dir = Path(self.config.get('paths.reports', 
                                             default=str(default_reports_dir)))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"PDF Report Generator initialized. wkhtmltopdf: {self.wkhtmltopdf_path}")
    
    def generate_daily_report(self, articles: List[Article], 
                            report_date: datetime = None) -> Optional[str]:
        """日次PDFレポート生成"""
        try:
            report_date = report_date or datetime.now()
            
            # HTML生成
            html_content = self.html_generator.generate_daily_report(articles, report_date)
            
            # PDF出力パス
            date_str = report_date.strftime('%Y%m%d')
            pdf_filename = f"daily_news_report_{date_str}.pdf"
            pdf_path = self.output_dir / "daily" / pdf_filename
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            
            # PDF生成
            success = self._generate_pdf_from_html(html_content, str(pdf_path))
            
            if success:
                logger.info(f"Daily PDF report generated: {pdf_path}")
                return str(pdf_path)
            else:
                logger.error("Failed to generate daily PDF report")
                return None
                
        except Exception as e:
            logger.error(f"Daily PDF report generation failed: {e}")
            return None
    
    def generate_emergency_report(self, articles: List[Article]) -> Optional[str]:
        """緊急PDFレポート生成"""
        try:
            # HTML生成
            html_content = self.html_generator.generate_emergency_report(articles)
            
            # PDF出力パス
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_filename = f"emergency_alert_{timestamp}.pdf"
            pdf_path = self.output_dir / "emergency" / pdf_filename
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            
            # PDF生成
            success = self._generate_pdf_from_html(html_content, str(pdf_path))
            
            if success:
                logger.info(f"Emergency PDF report generated: {pdf_path}")
                return str(pdf_path)
            else:
                logger.error("Failed to generate emergency PDF report")
                return None
                
        except Exception as e:
            logger.error(f"Emergency PDF report generation failed: {e}")
            return None
    
    def generate_weekly_summary(self, articles: List[Article], 
                              week_start: datetime) -> Optional[str]:
        """週次PDFサマリー生成"""
        try:
            # HTML生成
            html_content = self.html_generator.generate_weekly_summary(articles, week_start)
            
            # PDF出力パス
            week_str = week_start.strftime('%Y%m%d')
            pdf_filename = f"weekly_summary_{week_str}.pdf"
            pdf_path = self.output_dir / "weekly" / pdf_filename
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            
            # PDF生成
            success = self._generate_pdf_from_html(html_content, str(pdf_path))
            
            if success:
                logger.info(f"Weekly PDF summary generated: {pdf_path}")
                return str(pdf_path)
            else:
                logger.error("Failed to generate weekly PDF summary")
                return None
                
        except Exception as e:
            logger.error(f"Weekly PDF summary generation failed: {e}")
            return None
    
    def _generate_pdf_from_html(self, html_content: str, output_path: str) -> bool:
        """HTMLからPDF生成"""
        try:
            if not self.wkhtmltopdf_path:
                raise PDFGenerationError("wkhtmltopdf not found")
            
            # 一時HTMLファイル作成
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', 
                                           delete=False, encoding='utf-8') as temp_file:
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
                
                # PDF生成実行
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60  # 60秒タイムアウト
                )
                
                if result.returncode == 0:
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        logger.debug(f"PDF successfully generated: {output_path}")
                        return True
                    else:
                        logger.error(f"PDF file was not created or is empty: {output_path}")
                        return False
                else:
                    logger.error(f"wkhtmltopdf failed with return code {result.returncode}")
                    logger.error(f"STDOUT: {result.stdout}")
                    logger.error(f"STDERR: {result.stderr}")
                    return False
                    
            finally:
                # 一時ファイル削除
                try:
                    os.unlink(temp_html_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_html_path}: {e}")
            
        except subprocess.TimeoutExpired:
            logger.error("PDF generation timed out")
            return False
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            return False
    
    def _find_wkhtmltopdf(self) -> Optional[str]:
        """wkhtmltopdfのパスを探索"""
        
        # 設定ファイルから取得
        configured_path = self.config.get('pdf_generation.wkhtmltopdf_path')
        if configured_path and os.path.isfile(configured_path):
            return configured_path
        
        # 一般的なパスを検索
        possible_paths = [
            # Linux
            '/usr/bin/wkhtmltopdf',
            '/usr/local/bin/wkhtmltopdf',
            '/opt/wkhtmltopdf/bin/wkhtmltopdf',
            # Windows
            'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe',
            'C:\\Program Files (x86)\\wkhtmltopdf\\bin\\wkhtmltopdf.exe',
            # macOS
            '/usr/local/bin/wkhtmltopdf',
            '/opt/homebrew/bin/wkhtmltopdf'
        ]
        
        for path in possible_paths:
            if os.path.isfile(path):
                return path
        
        # PATH環境変数から検索
        try:
            result = subprocess.run(['which', 'wkhtmltopdf'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                path = result.stdout.strip()
                if os.path.isfile(path):
                    return path
        except Exception:
            pass
        
        # Windowsの場合はwhereコマンドも試行
        try:
            result = subprocess.run(['where', 'wkhtmltopdf'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                path = result.stdout.strip().split('\n')[0]  # 最初の結果を使用
                if os.path.isfile(path):
                    return path
        except Exception:
            pass
        
        logger.warning("wkhtmltopdf not found. PDF generation will not be available.")
        return None
    
    def generate_custom_pdf(self, html_content: str, 
                          filename: str = None,
                          options: Dict[str, Any] = None) -> Optional[str]:
        """カスタムPDF生成"""
        try:
            # ファイル名生成
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"custom_report_{timestamp}.pdf"
            
            # 拡張子確認
            if not filename.endswith('.pdf'):
                filename += '.pdf'
            
            pdf_path = self.output_dir / "custom" / filename
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            
            # オプション適用
            if options:
                original_options = self.pdf_options.copy()
                self.pdf_options.update(options)
            
            try:
                # PDF生成
                success = self._generate_pdf_from_html(html_content, str(pdf_path))
                
                if success:
                    logger.info(f"Custom PDF generated: {pdf_path}")
                    return str(pdf_path)
                else:
                    logger.error("Failed to generate custom PDF")
                    return None
                    
            finally:
                # オプションリストア
                if options:
                    self.pdf_options = original_options
                    
        except Exception as e:
            logger.error(f"Custom PDF generation failed: {e}")
            return None
    
    def get_pdf_info(self, pdf_path: str) -> Dict[str, Any]:
        """PDF情報取得"""
        try:
            if not os.path.exists(pdf_path):
                return {'error': 'File not found'}
            
            stat = os.stat(pdf_path)
            
            return {
                'file_path': pdf_path,
                'file_size': stat.st_size,
                'file_size_mb': round(stat.st_size / (1024 * 1024), 2),
                'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'exists': True
            }
            
        except Exception as e:
            return {'error': str(e), 'exists': False}
    
    def cleanup_old_reports(self, days_to_keep: int = 30) -> Dict[str, int]:
        """古いレポートのクリーンアップ"""
        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
            cleaned_counts = {'daily': 0, 'emergency': 0, 'weekly': 0, 'custom': 0}
            
            for report_type in ['daily', 'emergency', 'weekly', 'custom']:
                report_dir = self.output_dir / report_type
                
                if report_dir.exists():
                    for pdf_file in report_dir.glob('*.pdf'):
                        if pdf_file.stat().st_mtime < cutoff_date:
                            try:
                                pdf_file.unlink()
                                cleaned_counts[report_type] += 1
                                logger.debug(f"Deleted old PDF: {pdf_file}")
                            except Exception as e:
                                logger.warning(f"Failed to delete {pdf_file}: {e}")
            
            total_cleaned = sum(cleaned_counts.values())
            logger.info(f"Cleaned up {total_cleaned} old PDF reports")
            
            return cleaned_counts
            
        except Exception as e:
            logger.error(f"PDF cleanup failed: {e}")
            return {}
    
    def test_pdf_generation(self) -> Dict[str, Any]:
        """PDF生成機能テスト"""
        try:
            if not self.wkhtmltopdf_path:
                return {
                    'success': False,
                    'error': 'wkhtmltopdf not found'
                }
            
            # テスト用HTML
            test_html = '''
            <!DOCTYPE html>
            <html lang="ja">
            <head>
                <meta charset="UTF-8">
                <title>PDF Generation Test</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    h1 { color: #007bff; }
                </style>
            </head>
            <body>
                <h1>PDF生成テスト</h1>
                <p>このファイルはPDF生成機能のテストです。</p>
                <p>生成日時: ''' + datetime.now().strftime('%Y年%m月%d日 %H:%M:%S') + '''</p>
            </body>
            </html>
            '''
            
            # テストPDF生成
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            test_pdf_path = self.generate_custom_pdf(
                test_html, 
                f"pdf_test_{timestamp}.pdf"
            )
            
            if test_pdf_path:
                pdf_info = self.get_pdf_info(test_pdf_path)
                return {
                    'success': True,
                    'pdf_path': test_pdf_path,
                    'pdf_info': pdf_info,
                    'wkhtmltopdf_path': self.wkhtmltopdf_path
                }
            else:
                return {
                    'success': False,
                    'error': 'PDF generation failed'
                }
                
        except Exception as e:
            logger.error(f"PDF generation test failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# グローバルPDFジェネレーターインスタンス
_pdf_generator_instance = None


def get_pdf_generator() -> PDFReportGenerator:
    """グローバルPDFジェネレーターインスタンス取得"""
    global _pdf_generator_instance
    if _pdf_generator_instance is None:
        _pdf_generator_instance = PDFReportGenerator()
    return _pdf_generator_instance