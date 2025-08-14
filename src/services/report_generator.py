"""
Report generation service for HTML and PDF reports
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import time
import hashlib

from jinja2 import Environment, FileSystemLoader, Template
try:
    import weasyprint
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

from utils.config import get_config
from models.article import Article, ArticleCategory
from services.ai_analyzer import ClaudeAnalyzer


logger = logging.getLogger(__name__)


class ReportGenerationError(Exception):
    """Report generation specific error"""
    pass


class ReportGenerator:
    """Generate HTML and PDF reports from news articles"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        
        # Setup Jinja2 environment
        template_dir = Path(__file__).parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True
        )
        
        # Add custom filters
        self._setup_jinja_filters()
        
        # Configuration
        self.report_formats = self.config.get('reporting', 'formats', default=['html', 'pdf'])
        self.output_dir = self.config.get_storage_path('reports')
        
        # AI analyzer for daily summaries
        try:
            self.ai_analyzer = ClaudeAnalyzer(self.config)
        except Exception as e:
            logger.warning(f"AI analyzer not available: {e}")
            self.ai_analyzer = None
    
    def _setup_jinja_filters(self):
        """Setup custom Jinja2 filters"""
        
        def strftime_filter(date_str, format_str='%Y-%m-%d %H:%M'):
            """Format datetime string"""
            try:
                if isinstance(date_str, str):
                    # Try different string date formats
                    try:
                        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except ValueError:
                        # Try parsing other common formats
                        try:
                            dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            dt = datetime.strptime(date_str, '%Y-%m-%d')
                elif hasattr(date_str, 'strftime'):
                    # Already a datetime object
                    dt = date_str
                else:
                    # Fallback
                    return str(date_str)
                
                return dt.strftime(format_str)
            except Exception as e:
                logger.warning(f"strftime_filter error: {e} for date_str: {date_str}")
                return str(date_str)
        
        def round_filter(value, precision=2):
            """Round number to specified precision"""
            try:
                return round(float(value), precision)
            except (ValueError, TypeError):
                return value
        
        def truncate_filter(text, length=100, end='...'):
            """Truncate text to specified length"""
            if not text:
                return ''
            if len(text) <= length:
                return text
            return text[:length].rstrip() + end
        
        def sentiment_emoji_filter(sentiment_score):
            """Convert sentiment score to emoji"""
            if sentiment_score > 0.3:
                return '😊'
            elif sentiment_score < -0.3:
                return '😟'
            else:
                return '😐'
        
        def importance_color_filter(importance_score):
            """Get color class for importance score"""
            if importance_score >= 9:
                return 'importance-critical'
            elif importance_score >= 8:
                return 'importance-high'
            elif importance_score >= 6:
                return 'importance-medium'
            elif importance_score >= 4:
                return 'importance-low'
            else:
                return 'importance-minimal'
        
        def category_icon_filter(category):
            """Get icon for category"""
            icons = {
                'domestic_social': '🏠',
                'international_social': '🌍',
                'it_ai': '💻',
                'cybersecurity': '🔒',
                'technology': '⚡',
                'business': '💼',
                'science': '🔬',
                'health': '🏥',
                'environment': '🌱',
                'politics': '🏛️',
                'sports': '⚽',
                'entertainment': '🎭'
            }
            return icons.get(category, '📰')
        
        def format_number_filter(value):
            """Format number with commas"""
            try:
                return f"{int(value):,}"
            except (ValueError, TypeError):
                return value
        
        def risk_level_filter(importance_score, cvss_score=None):
            """Determine risk level based on scores"""
            if cvss_score and cvss_score >= 9.0:
                return 'critical'
            elif importance_score >= 9:
                return 'high'
            elif importance_score >= 7:
                return 'medium'
            elif importance_score >= 5:
                return 'low'
            else:
                return 'minimal'
        
        # Register filters
        self.jinja_env.filters['strftime'] = strftime_filter
        self.jinja_env.filters['round'] = round_filter
        self.jinja_env.filters['truncate'] = truncate_filter
        self.jinja_env.filters['sentiment_emoji'] = sentiment_emoji_filter
        self.jinja_env.filters['importance_color'] = importance_color_filter
        self.jinja_env.filters['category_icon'] = category_icon_filter
        self.jinja_env.filters['format_number'] = format_number_filter
        self.jinja_env.filters['risk_level'] = risk_level_filter
    
    async def generate_daily_report(self, articles: List[Article], 
                                  report_type: str = 'daily') -> Dict[str, str]:
        """Generate daily news report in multiple formats"""
        try:
            start_time = time.time()
            
            # Prepare report data
            report_data = await self._prepare_report_data(articles, report_type)
            
            # Generate reports
            generated_reports = {}
            
            if self.report_formats and 'html' in self.report_formats:
                html_path = await self._generate_html_report(report_data)
                generated_reports['html'] = str(html_path)
            
            if self.report_formats and 'pdf' in self.report_formats:
                pdf_path = await self._generate_pdf_report(report_data)
                generated_reports['pdf'] = str(pdf_path)
            
            processing_time = time.time() - start_time
            logger.info(f"Generated {len(generated_reports)} reports in {processing_time:.2f}s")
            
            return generated_reports
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            raise ReportGenerationError(f"Failed to generate report: {e}")
    
    async def generate_urgent_report(self, articles: List[Article]) -> Dict[str, str]:
        """Generate urgent news report in multiple formats"""
        return await self.generate_daily_report(articles, report_type='urgent')
    
    async def _prepare_report_data(self, articles: List[Article], 
                                 report_type: str) -> Dict[str, Any]:
        """Prepare data for report template"""
        
        # Basic statistics
        total_articles = len(articles)
        urgent_articles = [a for a in articles if a.is_urgent]
        urgent_count = len(urgent_articles)
        
        # Group articles by category
        articles_by_category = {}
        for category in ArticleCategory:
            category_articles = [a for a in articles if a.category == category]
            if category_articles:
                # Sort by importance score, then by published date
                category_articles.sort(
                    key=lambda x: (x.importance_score, x.published_at), 
                    reverse=True
                )
                articles_by_category[category.value] = category_articles
        
        # Advanced statistics
        statistics = self._calculate_advanced_statistics(articles)
        
        # Top articles by importance
        top_articles = sorted(articles, key=lambda x: x.importance_score, reverse=True)[:10]
        
        # Generate daily summary using AI
        daily_summary = ""
        if self.ai_analyzer and articles:
            try:
                daily_summary = await self.ai_analyzer.create_daily_summary(articles)
            except Exception as e:
                logger.warning(f"Failed to generate daily summary: {e}")
        
        # Security alerts
        security_articles = [a for a in articles if 
                           hasattr(a, 'cvss_score') and a.cvss_score and a.cvss_score >= 7.0]
        
        # Trending keywords
        all_keywords = []
        for article in articles:
            if hasattr(article, 'keywords') and article.keywords:
                all_keywords.extend(article.keywords)
        
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        trending_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Report metadata
        now = datetime.now()
        report_title = self._get_report_title(report_type, now)
        
        return {
            'report_title': report_title,
            'delivery_date': now.strftime('%Y年%m月%d日 %H:%M'),
            'generation_time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'total_articles': total_articles,
            'urgent_articles': urgent_count,
            'urgent_articles_list': urgent_articles[:5],  # Top 5 urgent
            'categories_count': len(articles_by_category),
            'articles_by_category': articles_by_category,
            'top_articles': top_articles,
            'security_articles': security_articles,
            'trending_keywords': trending_keywords,
            'statistics': statistics,
            'daily_summary': daily_summary,
            'processing_time': 0,  # Will be updated later
            'version': self.config.get('general', 'version', default='1.0.0'),
            'report_type': report_type
        }
    
    def _calculate_advanced_statistics(self, articles: List[Article]) -> Dict[str, Any]:
        """Calculate comprehensive statistics"""
        if not articles:
            return {}
        
        # Basic stats
        total_articles = len(articles)
        
        # Importance distribution
        importance_scores = [a.importance_score for a in articles]
        avg_importance = sum(importance_scores) / total_articles
        max_importance = max(importance_scores)
        min_importance = min(importance_scores)
        
        # Importance level counts
        critical_count = len([a for a in articles if a.importance_score >= 9])
        high_count = len([a for a in articles if 7 <= a.importance_score < 9])
        medium_count = len([a for a in articles if 5 <= a.importance_score < 7])
        low_count = len([a for a in articles if a.importance_score < 5])
        
        # Sentiment analysis
        sentiment_scores = [a.sentiment_score for a in articles if hasattr(a, 'sentiment_score')]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        positive_count = len([s for s in sentiment_scores if s > 0.1])
        negative_count = len([s for s in sentiment_scores if s < -0.1])
        neutral_count = len([s for s in sentiment_scores if -0.1 <= s <= 0.1])
        
        # Language distribution
        language_counts = {}
        for article in articles:
            lang = getattr(article, 'language', 'unknown')
            language_counts[lang] = language_counts.get(lang, 0) + 1
        
        # Source distribution
        source_counts = {}
        for article in articles:
            source = getattr(article, 'source', {})
            source_name = source.get('name', 'Unknown') if isinstance(source, dict) else str(source)
            source_counts[source_name] = source_counts.get(source_name, 0) + 1
        
        # Time distribution (articles by hour)
        hour_counts = {}
        for article in articles:
            if hasattr(article, 'published_at') and article.published_at:
                try:
                    if isinstance(article.published_at, str):
                        dt = datetime.fromisoformat(article.published_at.replace('Z', '+00:00'))
                    else:
                        dt = article.published_at
                    hour = dt.hour
                    hour_counts[hour] = hour_counts.get(hour, 0) + 1
                except Exception:
                    pass
        
        return {
            'avg_importance': round(avg_importance, 2),
            'max_importance': max_importance,
            'min_importance': min_importance,
            'importance_distribution': {
                'critical': critical_count,
                'high': high_count,
                'medium': medium_count,
                'low': low_count
            },
            'sentiment_analysis': {
                'avg_sentiment': round(avg_sentiment, 2),
                'positive_count': positive_count,
                'negative_count': negative_count,
                'neutral_count': neutral_count
            },
            'language_distribution': dict(sorted(language_counts.items(), key=lambda x: x[1], reverse=True)[:5]),
            'source_distribution': dict(sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:5]),
            'time_distribution': hour_counts
        }
    
    def _get_report_title(self, report_type: str, date: datetime) -> str:
        """Generate report title based on type and date"""
        date_str = date.strftime('%Y年%m月%d日')
        
        if report_type == 'daily':
            return f"ニュース配信レポート - {date_str}"
        elif report_type == 'urgent':
            return f"緊急ニュース速報 - {date_str}"
        elif report_type == 'weekly':
            return f"週間ニュースまとめ - {date_str}"
        else:
            return f"ニュースレポート - {date_str}"
    
    async def _generate_html_report(self, report_data: Dict[str, Any]) -> Path:
        """Generate HTML report"""
        try:
            # Select template based on report type
            report_type = report_data.get('report_type', 'daily')
            template_name = self._get_template_name(report_type)
            
            template = self.jinja_env.get_template(template_name)
            
            # Render HTML
            html_content = template.render(**report_data)
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            type_prefix = report_type if report_type != 'daily' else 'news'
            filename = f"{type_prefix}_report_{timestamp}.html"
            html_path = self.output_dir / filename
            
            # Write HTML file
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Generated HTML report: {html_path}")
            return html_path
            
        except Exception as e:
            logger.error(f"HTML report generation failed: {e}")
            raise ReportGenerationError(f"HTML generation failed: {e}")
    
    def _get_template_name(self, report_type: str) -> str:
        """Get template name based on report type"""
        template_mapping = {
            'daily': 'report_template.html',
            'urgent': 'urgent_alert_template.html',
            'weekly': 'weekly_summary_template.html',
            'monthly': 'report_template.html'  # Use default for monthly
        }
        return template_mapping.get(report_type, 'report_template.html')
    
    async def _generate_pdf_report(self, report_data: Dict[str, Any]) -> Path:
        """Generate PDF report from HTML template"""
        try:
            # Load PDF-optimized template
            template_name = 'pdf_report_template.html'
            try:
                template = self.jinja_env.get_template(template_name)
            except Exception:
                # Fallback to regular template
                template = self.jinja_env.get_template('report_template.html')
            
            # Render HTML with PDF optimizations
            html_content = template.render(**report_data, pdf_mode=True)
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"news_report_{timestamp}.pdf"
            pdf_path = self.output_dir / filename
            
            # Convert HTML to PDF with multiple methods
            success = await self._html_to_pdf_multi_method(html_content, pdf_path)
            
            if not success:
                raise ReportGenerationError("All PDF generation methods failed")
            
            logger.info(f"Generated PDF report: {pdf_path}")
            return pdf_path
            
        except Exception as e:
            logger.error(f"PDF report generation failed: {e}")
            raise ReportGenerationError(f"PDF generation failed: {e}")
    
    async def _html_to_pdf_multi_method(self, html_content: str, output_path: Path) -> bool:
        """Convert HTML to PDF using multiple methods for reliability"""
        methods = [
            ('wkhtmltopdf', self._wkhtmltopdf_to_pdf),
            ('Playwright', self._playwright_to_pdf)
        ]
        
        if WEASYPRINT_AVAILABLE:
            methods.insert(0, ('WeasyPrint', self._weasyprint_to_pdf))
        
        for method_name, method_func in methods:
            try:
                logger.info(f"Attempting PDF generation with {method_name}")
                loop = asyncio.get_event_loop()
                
                await loop.run_in_executor(
                    None,
                    method_func,
                    html_content,
                    output_path
                )
                
                if output_path.exists() and output_path.stat().st_size > 0:
                    logger.info(f"PDF generated successfully with {method_name}")
                    return True
                    
            except Exception as e:
                logger.warning(f"{method_name} PDF generation failed: {e}")
                continue
        
        return False
    
    def _weasyprint_to_pdf(self, html_content: str, output_path: Path):
        """WeasyPrint HTML to PDF conversion"""
        if not WEASYPRINT_AVAILABLE:
            raise ReportGenerationError("WeasyPrint not available for PDF generation")
        # Enhanced CSS for PDF
        pdf_css = CSS(string="""
            @page {
                size: A4;
                margin: 1.5cm;
                @top-right {
                    content: "ニュース配信レポート";
                    font-size: 10px;
                    color: #666;
                }
                @bottom-center {
                    content: counter(page) " / " counter(pages);
                    font-size: 10px;
                    color: #666;
                }
            }
            
            body {
                font-size: 11px;
                font-family: 'Noto Sans CJK JP', 'Arial', sans-serif;
                line-height: 1.4;
                color: #333;
            }
            
            .container {
                box-shadow: none !important;
                padding: 0 !important;
                margin: 0 !important;
            }
            
            .header {
                border-bottom: 2px solid #2c3e50;
                margin-bottom: 20px;
            }
            
            .header h1 {
                font-size: 20px;
                margin: 0 0 10px 0;
            }
            
            .summary {
                background-color: #f8f9fa;
                padding: 15px;
                border-left: 4px solid #3498db;
                margin-bottom: 20px;
                page-break-inside: avoid;
            }
            
            .stats {
                display: flex;
                justify-content: space-around;
                margin-bottom: 20px;
                page-break-inside: avoid;
            }
            
            .stat-item {
                text-align: center;
                padding: 10px;
                background-color: #3498db;
                color: white;
                border-radius: 5px;
                margin: 2px;
                min-width: 100px;
            }
            
            .stat-number {
                font-size: 18px;
                font-weight: bold;
                display: block;
            }
            
            .urgent-alerts {
                background-color: #e74c3c;
                color: white;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                page-break-inside: avoid;
            }
            
            .category-section {
                margin-bottom: 25px;
                page-break-inside: avoid;
            }
            
            .category-header {
                background-color: #34495e;
                color: white;
                padding: 10px 15px;
                border-radius: 5px 5px 0 0;
                margin: 0;
                font-size: 14px;
                font-weight: bold;
            }
            
            .category-content {
                border: 1px solid #bdc3c7;
                border-top: none;
                border-radius: 0 0 5px 5px;
            }
            
            .article {
                padding: 15px;
                border-bottom: 1px solid #ecf0f1;
                page-break-inside: avoid;
            }
            
            .article:last-child {
                border-bottom: none;
            }
            
            .article-title {
                font-size: 12px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 8px;
            }
            
            .article-title a {
                color: #2c3e50;
                text-decoration: none;
            }
            
            .article-meta {
                color: #7f8c8d;
                font-size: 9px;
                margin-bottom: 8px;
            }
            
            .article-summary {
                margin-bottom: 10px;
                line-height: 1.5;
                font-size: 10px;
            }
            
            .article-footer {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .importance-score {
                background-color: #e67e22;
                color: white;
                padding: 3px 8px;
                border-radius: 10px;
                font-size: 8px;
                font-weight: bold;
            }
            
            .importance-critical { background-color: #c0392b; }
            .importance-high { background-color: #e74c3c; }
            .importance-medium { background-color: #f39c12; }
            .importance-low { background-color: #27ae60; }
            .importance-minimal { background-color: #95a5a6; }
            
            .keywords {
                margin-top: 5px;
            }
            
            .keyword {
                background-color: #3498db;
                color: white;
                padding: 2px 6px;
                border-radius: 8px;
                font-size: 8px;
                margin-right: 3px;
                display: inline-block;
            }
            
            .cvss-score {
                background-color: #9b59b6;
                color: white;
                padding: 3px 8px;
                border-radius: 10px;
                font-size: 8px;
                font-weight: bold;
                margin-left: 5px;
            }
            
            .footer {
                text-align: center;
                margin-top: 30px;
                padding-top: 15px;
                border-top: 1px solid #bdc3c7;
                color: #7f8c8d;
                font-size: 9px;
            }
            
            .page-break {
                page-break-before: always;
            }
            
            .no-break {
                page-break-inside: avoid;
            }
        """)
        
        # Generate PDF
        html_doc = HTML(string=html_content)
        html_doc.write_pdf(output_path, stylesheets=[pdf_css])
    
    def _wkhtmltopdf_to_pdf(self, html_content: str, output_path: Path):
        """wkhtmltopdf HTML to PDF conversion"""
        import subprocess
        import tempfile
        
        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_html:
            temp_html.write(html_content)
            temp_html_path = temp_html.name
        
        try:
            # wkhtmltopdf command
            wkhtmltopdf_cmd = [
                'wkhtmltopdf',
                '--page-size', 'A4',
                '--margin-top', '1.5cm',
                '--margin-right', '1.5cm',
                '--margin-bottom', '1.5cm',
                '--margin-left', '1.5cm',
                '--encoding', 'UTF-8',
                '--enable-local-file-access',
                '--print-media-type',
                '--footer-center', '[page]/[topage]',
                '--footer-font-size', '8',
                temp_html_path,
                str(output_path)
            ]
            
            # Execute wkhtmltopdf
            result = subprocess.run(
                wkhtmltopdf_cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                raise Exception(f"wkhtmltopdf failed: {result.stderr}")
                
        finally:
            # Clean up temporary file
            Path(temp_html_path).unlink(missing_ok=True)
    
    def _playwright_to_pdf(self, html_content: str, output_path: Path):
        """Playwright HTML to PDF conversion (fallback method)"""
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                
                # Set HTML content
                page.set_content(html_content)
                
                # Generate PDF
                page.pdf(
                    path=str(output_path),
                    format='A4',
                    margin={
                        'top': '1.5cm',
                        'right': '1.5cm',
                        'bottom': '1.5cm',
                        'left': '1.5cm'
                    },
                    print_background=True,
                    display_header_footer=True,
                    header_template='<div style="font-size:10px;text-align:center;width:100%;color:#666;">ニュース配信レポート</div>',
                    footer_template='<div style="font-size:10px;text-align:center;width:100%;color:#666;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>'
                )
                
                browser.close()
                
        except ImportError:
            raise Exception("Playwright not available - install with: pip install playwright")
    
    async def generate_urgent_alert(self, urgent_articles: List[Article]) -> Dict[str, str]:
        """Generate urgent alert report"""
        try:
            if not urgent_articles:
                logger.warning("No urgent articles to generate alert for")
                return {}
            
            # Prepare urgent report data
            report_data = await self._prepare_urgent_report_data(urgent_articles)
            
            # Generate reports
            generated_reports = {}
            
            if self.report_formats and 'html' in self.report_formats:
                html_path = await self._generate_html_report(report_data)
                generated_reports['html'] = str(html_path)
            
            if self.report_formats and 'pdf' in self.report_formats:
                pdf_path = await self._generate_pdf_report(report_data)
                generated_reports['pdf'] = str(pdf_path)
            
            logger.info(f"Generated urgent alert with {len(urgent_articles)} articles")
            return generated_reports
            
        except Exception as e:
            logger.error(f"Urgent alert generation failed: {e}")
            raise ReportGenerationError(f"Failed to generate urgent alert: {e}")
    
    async def _prepare_urgent_report_data(self, urgent_articles: List[Article]) -> Dict[str, Any]:
        """Prepare data for urgent alert report"""
        
        # Sort by importance and CVSS score
        urgent_articles.sort(
            key=lambda x: (x.importance_score, x.cvss_score or 0), 
            reverse=True
        )
        
        # Group by category for urgent articles
        articles_by_category = {}
        for category in ArticleCategory:
            category_articles = [a for a in urgent_articles if a.category == category]
            if category_articles:
                articles_by_category[category.value] = category_articles
        
        now = datetime.now()
        
        return {
            'report_title': f"🚨 緊急ニュース速報 - {now.strftime('%Y年%m月%d日 %H:%M')}",
            'delivery_date': now.strftime('%Y年%m月%d日 %H:%M'),
            'generation_time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'total_articles': len(urgent_articles),
            'urgent_articles': len(urgent_articles),
            'urgent_articles_list': urgent_articles,
            'categories_count': len(articles_by_category),
            'avg_importance': sum(a.importance_score for a in urgent_articles) / len(urgent_articles),
            'articles_by_category': articles_by_category,
            'daily_summary': f"{len(urgent_articles)}件の緊急ニュースが検出されました。",
            'processing_time': 0,
            'version': self.config.get('general', 'version', default='1.0.0'),
            'report_type': 'urgent'
        }
    
    def get_report_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get metadata for generated report"""
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {}
            
            stat = path.stat()
            
            return {
                'file_path': str(path),
                'file_name': path.name,
                'file_size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'format': path.suffix.lower().replace('.', ''),
                'size_mb': round(stat.st_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to get report metadata: {e}")
            return {}
    
    def cleanup_old_reports(self, days_to_keep: int = 30):
        """Clean up old report files"""
        try:
            cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
            deleted_count = 0
            
            for file_path in self.output_dir.glob("news_report_*"):
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old reports")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Report cleanup failed: {e}")
            return 0
    
    def get_recent_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of recent reports"""
        try:
            reports = []
            
            for file_path in self.output_dir.glob("news_report_*"):
                metadata = self.get_report_metadata(str(file_path))
                if metadata:
                    reports.append(metadata)
            
            # Sort by creation time (newest first)
            reports.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return reports[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get recent reports: {e}")
            return []
    
    def calculate_content_hash(self, articles: List[Article]) -> str:
        """Calculate hash of article content for change detection"""
        content_strings = []
        
        for article in articles:
            content_str = f"{article.title}|{article.url}|{article.importance_score}"
            content_strings.append(content_str)
        
        combined_content = "|".join(sorted(content_strings))
        return hashlib.md5(combined_content.encode('utf-8')).hexdigest()
    
    def is_report_generation_enabled(self) -> bool:
        """Check if report generation is enabled"""
        return (
            self.config.get('reporting', 'enabled', default=True) and
            self.report_formats and len(self.report_formats) > 0
        )
    
    async def generate_weekly_report(self, articles: List[Article], 
                                   start_date: datetime, end_date: datetime) -> Dict[str, str]:
        """Generate weekly summary report"""
        try:
            # Prepare weekly report data
            report_data = await self._prepare_weekly_report_data(articles, start_date, end_date)
            
            # Generate reports
            generated_reports = {}
            
            if self.report_formats and 'html' in self.report_formats:
                html_path = await self._generate_html_report(report_data)
                generated_reports['html'] = str(html_path)
            
            if self.report_formats and 'pdf' in self.report_formats:
                pdf_path = await self._generate_pdf_report(report_data)
                generated_reports['pdf'] = str(pdf_path)
            
            logger.info(f"Generated weekly report with {len(articles)} articles")
            return generated_reports
            
        except Exception as e:
            logger.error(f"Weekly report generation failed: {e}")
            raise ReportGenerationError(f"Failed to generate weekly report: {e}")
    
    async def _prepare_weekly_report_data(self, articles: List[Article], 
                                        start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Prepare data for weekly report"""
        
        # Basic statistics
        total_articles = len(articles)
        urgent_articles = [a for a in articles if getattr(a, 'is_urgent', False)]
        urgent_count = len(urgent_articles)
        
        # Time period information
        period_days = (end_date - start_date).days + 1
        
        # Category analysis
        category_analysis = self._analyze_categories_weekly(articles)
        
        # Top articles by importance
        top_articles = sorted(articles, key=lambda x: getattr(x, 'importance_score', 5), reverse=True)[:10]
        
        # Security articles
        security_articles = [a for a in articles if 
                           getattr(a, 'category', '') == 'cybersecurity' or
                           (hasattr(a, 'cvss_score') and getattr(a, 'cvss_score', None) and a.cvss_score >= 7.0)]
        
        # Weekly summary
        weekly_summary = ""
        if self.ai_analyzer and articles:
            try:
                weekly_summary = await self.ai_analyzer.create_weekly_summary(articles)
            except Exception as e:
                logger.warning(f"Failed to generate weekly summary: {e}")
        
        # Advanced statistics
        statistics = self._calculate_advanced_statistics(articles)
        
        # Trending keywords for the week
        trending_keywords = self._calculate_weekly_trending_keywords(articles)
        
        # Additional weekly metrics
        unique_sources = len(set(
            getattr(getattr(a, 'source', {}), 'name', 'Unknown') 
            if isinstance(getattr(a, 'source', {}), dict) 
            else str(getattr(a, 'source', 'Unknown'))
            for a in articles
        ))
        
        now = datetime.now()
        
        return {
            'report_title': f"週間ニュース総括レポート - {start_date.strftime('%Y年%m月%d日')}〜{end_date.strftime('%m月%d日')}",
            'delivery_date': now.strftime('%Y年%m月%d日 %H:%M'),
            'generation_time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'start_date': start_date,
            'end_date': end_date,
            'period_days': period_days,
            'total_articles': total_articles,
            'urgent_articles': urgent_count,
            'categories_count': len(category_analysis),
            'avg_importance': sum(getattr(a, 'importance_score', 5) for a in articles) / total_articles if articles else 0,
            'unique_sources': unique_sources,
            'processing_time': 0,  # Will be updated
            'top_articles': top_articles,
            'security_articles': security_articles,
            'category_analysis': category_analysis,
            'trending_keywords': trending_keywords,
            'statistics': statistics,
            'weekly_summary': weekly_summary,
            'top_categories': list(category_analysis.keys())[:5],
            'version': self.config.get('general', 'version', default='1.0.0'),
            'report_type': 'weekly'
        }
    
    def _analyze_categories_weekly(self, articles: List[Article]) -> Dict[str, Dict[str, Any]]:
        """Analyze articles by category for weekly report"""
        category_data = {}
        
        for article in articles:
            category = getattr(article, 'detailed_category', 
                             getattr(article, 'category', '未分類'))
            
            if category not in category_data:
                category_data[category] = {
                    'count': 0,
                    'urgent_count': 0,
                    'total_importance': 0,
                    'keywords': []
                }
            
            cat_data = category_data[category]
            cat_data['count'] += 1
            cat_data['total_importance'] += getattr(article, 'importance_score', 5)
            
            if getattr(article, 'is_urgent', False):
                cat_data['urgent_count'] += 1
            
            if hasattr(article, 'keywords') and getattr(article, 'keywords', None):
                cat_data['keywords'].extend(article.keywords)
        
        # Calculate averages and top keywords
        for category, data in category_data.items():
            data['avg_importance'] = data['total_importance'] / data['count'] if data['count'] > 0 else 0
            
            # Count keyword frequency
            keyword_counts = {}
            for keyword in data['keywords']:
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
            
            data['top_keywords'] = [k for k, v in sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
        
        return category_data
    
    def _calculate_weekly_trending_keywords(self, articles: List[Article]) -> List[tuple]:
        """Calculate trending keywords for the week"""
        all_keywords = []
        for article in articles:
            if hasattr(article, 'keywords') and getattr(article, 'keywords', None):
                all_keywords.extend(article.keywords)
        
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        return sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:15]