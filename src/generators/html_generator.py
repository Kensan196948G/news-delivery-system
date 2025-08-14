"""
HTML Report Generator
HTMLレポート生成モジュール - Jinja2テンプレート使用
"""

import sys
import os
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, Template

from models.article import Article, ArticleCategory
from utils.config import get_config

logger = logging.getLogger(__name__)


class HTMLReportGenerator:
    """HTMLレポート生成"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        
        # テンプレートディレクトリ - 相対パスで設定
        project_root = Path(__file__).parent.parent.parent
        default_templates_dir = project_root / 'src' / 'templates'
        template_dir = self.config.get('paths.templates', 
                                     default=str(default_templates_dir))
        
        if os.path.exists(template_dir):
            self.env = Environment(loader=FileSystemLoader(template_dir))
        else:
            # フォールバック: インラインテンプレート使用
            self.env = Environment()
            logger.warning(f"Template directory not found: {template_dir}. Using inline templates.")
        
        logger.info("HTML Report Generator initialized")
    
    def generate_daily_report(self, articles: List[Article], 
                            report_date: datetime = None) -> str:
        """日次レポート生成"""
        try:
            report_date = report_date or datetime.now()
            
            # 記事を重要度順にソート
            sorted_articles = sorted(articles, 
                                   key=lambda x: getattr(x, 'importance_score', 5), 
                                   reverse=True)
            
            # カテゴリ別に整理
            categorized_articles = self._categorize_articles(sorted_articles)
            
            # 統計情報
            stats = self._generate_statistics(sorted_articles)
            
            # 緊急アラート
            alerts = self._extract_urgent_alerts(sorted_articles)
            
            # テンプレートデータ準備
            template_data = {
                'report_date': report_date,
                'report_title': f'ニュース配信レポート - {report_date.strftime("%Y年%m月%d日")}',
                'total_articles': len(articles),
                'articles': sorted_articles,
                'categorized_articles': categorized_articles,
                'statistics': stats,
                'urgent_alerts': alerts,
                'generated_at': datetime.now(),
                'report_type': 'daily'
            }
            
            # HTML生成
            try:
                template = self.env.get_template('report_template.html')
                html_content = template.render(**template_data)
            except Exception as e:
                logger.warning(f"Template file not found: {e}. Using inline template.")
                html_content = self._generate_inline_template(**template_data)
            
            logger.info(f"Daily HTML report generated: {len(articles)} articles")
            return html_content
            
        except Exception as e:
            logger.error(f"Failed to generate daily HTML report: {e}")
            return self._generate_error_report(f"レポート生成エラー: {str(e)}")
    
    def generate_emergency_report(self, articles: List[Article]) -> str:
        """緊急レポート生成"""
        try:
            # 緊急記事のみフィルタ
            urgent_articles = [a for a in articles 
                             if getattr(a, 'importance_score', 0) >= 9 
                             or getattr(a, 'cvss_score', 0) >= 9.0]
            
            # テンプレートデータ準備
            template_data = {
                'report_date': datetime.now(),
                'report_title': '緊急ニュースアラート',
                'total_articles': len(urgent_articles),
                'articles': urgent_articles,
                'generated_at': datetime.now(),
                'report_type': 'emergency'
            }
            
            # 緊急テンプレート使用
            try:
                template = self.env.get_template('urgent_alert_template.html')
                html_content = template.render(**template_data)
            except Exception as e:
                logger.warning(f"Emergency template not found: {e}. Using inline template.")
                html_content = self._generate_emergency_inline_template(**template_data)
            
            logger.info(f"Emergency HTML report generated: {len(urgent_articles)} urgent articles")
            return html_content
            
        except Exception as e:
            logger.error(f"Failed to generate emergency HTML report: {e}")
            return self._generate_error_report(f"緊急レポート生成エラー: {str(e)}")
    
    def generate_weekly_summary(self, articles: List[Article], 
                              week_start: datetime) -> str:
        """週次サマリー生成"""
        try:
            week_end = week_start.replace(hour=23, minute=59, second=59)
            
            # 週次統計
            weekly_stats = self._generate_weekly_statistics(articles)
            
            # トップ記事
            top_articles = sorted(articles, 
                                key=lambda x: getattr(x, 'importance_score', 5), 
                                reverse=True)[:10]
            
            template_data = {
                'week_start': week_start,
                'week_end': week_end,
                'report_title': f'週次サマリー - {week_start.strftime("%Y年%m月%d日")}週',
                'total_articles': len(articles),
                'top_articles': top_articles,
                'statistics': weekly_stats,
                'generated_at': datetime.now(),
                'report_type': 'weekly'
            }
            
            try:
                template = self.env.get_template('weekly_summary_template.html')
                html_content = template.render(**template_data)
            except Exception as e:
                logger.warning(f"Weekly template not found: {e}. Using inline template.")
                html_content = self._generate_weekly_inline_template(**template_data)
            
            logger.info(f"Weekly HTML summary generated: {len(articles)} articles")
            return html_content
            
        except Exception as e:
            logger.error(f"Failed to generate weekly HTML summary: {e}")
            return self._generate_error_report(f"週次サマリー生成エラー: {str(e)}")
    
    def _categorize_articles(self, articles: List[Article]) -> Dict[str, List[Article]]:
        """記事のカテゴリ別分類"""
        categories = {
            '国内社会': [],
            '国際社会': [],
            '国内経済': [],
            '国際経済': [],
            'IT・AI': [],
            'セキュリティ': []
        }
        
        category_mapping = {
            ArticleCategory.DOMESTIC_SOCIAL: '国内社会',
            ArticleCategory.INTERNATIONAL_SOCIAL: '国際社会',
            ArticleCategory.DOMESTIC_ECONOMY: '国内経済', 
            ArticleCategory.INTERNATIONAL_ECONOMY: '国際経済',
            ArticleCategory.TECH: 'IT・AI',
            ArticleCategory.SECURITY: 'セキュリティ'
        }
        
        for article in articles:
            category = getattr(article, 'category', None)
            if category:
                category_name = category_mapping.get(category, 'その他')
                if category_name in categories:
                    categories[category_name].append(article)
                elif 'その他' not in categories:
                    categories['その他'] = [article]
                else:
                    categories['その他'].append(article)
        
        # 空のカテゴリを削除
        return {k: v for k, v in categories.items() if v}
    
    def _generate_statistics(self, articles: List[Article]) -> Dict[str, Any]:
        """統計情報生成"""
        if not articles:
            return {}
        
        importance_scores = [getattr(a, 'importance_score', 5) for a in articles]
        
        stats = {
            'total_count': len(articles),
            'avg_importance': sum(importance_scores) / len(importance_scores),
            'high_importance': len([s for s in importance_scores if s >= 8]),
            'medium_importance': len([s for s in importance_scores if 5 <= s < 8]),
            'low_importance': len([s for s in importance_scores if s < 5]),
            'urgent_count': len([a for a in articles if getattr(a, 'importance_score', 0) >= 9]),
            'security_count': len([a for a in articles 
                                 if getattr(a, 'category', None) == ArticleCategory.SECURITY])
        }
        
        # カテゴリ別統計
        category_counts = {}
        for article in articles:
            category = getattr(article, 'category', None)
            if category:
                category_name = category.value if hasattr(category, 'value') else str(category)
                category_counts[category_name] = category_counts.get(category_name, 0) + 1
        
        stats['category_breakdown'] = category_counts
        
        return stats
    
    def _generate_weekly_statistics(self, articles: List[Article]) -> Dict[str, Any]:
        """週次統計生成"""
        daily_counts = {}
        category_trends = {}
        
        for article in articles:
            # 日別カウント
            pub_date = getattr(article, 'published_at', datetime.now())
            if isinstance(pub_date, str):
                pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
            
            day_key = pub_date.strftime('%Y-%m-%d')
            daily_counts[day_key] = daily_counts.get(day_key, 0) + 1
            
            # カテゴリトレンド
            category = getattr(article, 'category', None)
            if category:
                cat_name = category.value if hasattr(category, 'value') else str(category)
                if cat_name not in category_trends:
                    category_trends[cat_name] = {}
                category_trends[cat_name][day_key] = category_trends[cat_name].get(day_key, 0) + 1
        
        return {
            'daily_counts': daily_counts,
            'category_trends': category_trends,
            'peak_day': max(daily_counts, key=daily_counts.get) if daily_counts else None,
            'total_days': len(daily_counts)
        }
    
    def _extract_urgent_alerts(self, articles: List[Article]) -> List[Article]:
        """緊急アラート記事抽出"""
        urgent_articles = []
        
        for article in articles:
            importance = getattr(article, 'importance_score', 0)
            cvss_score = getattr(article, 'cvss_score', 0)
            
            if importance >= 9 or cvss_score >= 9.0:
                urgent_articles.append(article)
        
        # 重要度順にソート
        return sorted(urgent_articles, 
                     key=lambda x: getattr(x, 'importance_score', 0), 
                     reverse=True)
    
    def _generate_inline_template(self, **data) -> str:
        """インライン日次レポートテンプレート"""
        template_str = '''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ report_title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        .header { border-bottom: 2px solid #007bff; padding-bottom: 20px; margin-bottom: 30px; }
        .header h1 { color: #007bff; margin: 0; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .stat-card { background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid #007bff; }
        .urgent-alerts { background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 6px; padding: 15px; margin-bottom: 30px; }
        .urgent-alerts h2 { color: #856404; margin-top: 0; }
        .category-section { margin-bottom: 40px; }
        .category-section h2 { color: #495057; border-bottom: 2px solid #e9ecef; padding-bottom: 10px; }
        .article { background: white; border: 1px solid #dee2e6; border-radius: 6px; padding: 15px; margin-bottom: 15px; }
        .article h3 { margin: 0 0 10px 0; color: #007bff; }
        .article-meta { font-size: 0.9em; color: #6c757d; margin-bottom: 10px; }
        .importance-badge { padding: 2px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; }
        .importance-high { background-color: #dc3545; color: white; }
        .importance-medium { background-color: #ffc107; color: #212529; }
        .importance-low { background-color: #28a745; color: white; }
        .footer { margin-top: 40px; text-align: center; font-size: 0.9em; color: #6c757d; }
        .keywords { margin-top: 10px; }
        .keyword-tag { display: inline-block; background: #e9ecef; padding: 2px 8px; border-radius: 4px; margin: 2px; font-size: 0.8em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ report_title }}</h1>
            <p>生成日時: {{ generated_at.strftime('%Y年%m月%d日 %H:%M:%S') }}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>総記事数</h3>
                <p><strong>{{ total_articles }}</strong> 件</p>
            </div>
            {% if statistics.urgent_count > 0 %}
            <div class="stat-card" style="border-left-color: #dc3545;">
                <h3>緊急記事</h3>
                <p><strong>{{ statistics.urgent_count }}</strong> 件</p>
            </div>
            {% endif %}
            <div class="stat-card">
                <h3>平均重要度</h3>
                <p><strong>{{ "%.1f"|format(statistics.avg_importance) }}</strong></p>
            </div>
            {% if statistics.security_count > 0 %}
            <div class="stat-card" style="border-left-color: #fd7e14;">
                <h3>セキュリティ関連</h3>
                <p><strong>{{ statistics.security_count }}</strong> 件</p>
            </div>
            {% endif %}
        </div>
        
        {% if urgent_alerts %}
        <div class="urgent-alerts">
            <h2>🚨 緊急アラート</h2>
            {% for article in urgent_alerts %}
            <div class="article">
                <h3>{{ article.translated_title or article.title }}</h3>
                <div class="article-meta">
                    <span class="importance-badge importance-high">重要度: {{ article.importance_score or 'N/A' }}</span>
                    {% if article.cvss_score %}
                    <span class="importance-badge importance-high">CVSS: {{ article.cvss_score }}</span>
                    {% endif %}
                    <span>{{ article.source }}</span>
                </div>
                <p>{{ article.summary or (article.translated_content or article.content)[:200] + '...' if (article.translated_content or article.content) }}</p>
                {% if article.keywords %}
                <div class="keywords">
                    {% for keyword in article.keywords %}
                    <span class="keyword-tag">{{ keyword }}</span>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        {% for category, category_articles in categorized_articles.items() %}
        <div class="category-section">
            <h2>{{ category }} ({{ category_articles|length }}件)</h2>
            {% for article in category_articles[:10] %}
            <div class="article">
                <h3>{{ article.translated_title or article.title }}</h3>
                <div class="article-meta">
                    {% set importance = article.importance_score or 5 %}
                    <span class="importance-badge {% if importance >= 8 %}importance-high{% elif importance >= 5 %}importance-medium{% else %}importance-low{% endif %}">
                        重要度: {{ importance }}
                    </span>
                    <span>{{ article.source }}</span>
                    {% if article.published_at %}
                    <span>{{ article.published_at[:10] if article.published_at is string else article.published_at.strftime('%Y-%m-%d') }}</span>
                    {% endif %}
                </div>
                <p>{{ article.summary or (article.translated_content or article.content)[:200] + '...' if (article.translated_content or article.content) }}</p>
                {% if article.keywords %}
                <div class="keywords">
                    {% for keyword in article.keywords %}
                    <span class="keyword-tag">{{ keyword }}</span>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% endfor %}
        
        <div class="footer">
            <p>このレポートは自動生成されました | News Delivery System</p>
        </div>
    </div>
</body>
</html>
        '''
        
        template = Template(template_str)
        return template.render(**data)
    
    def _generate_emergency_inline_template(self, **data) -> str:
        """インライン緊急レポートテンプレート"""
        template_str = '''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ report_title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #fff3cd; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; border: 2px solid #dc3545; }
        .header { text-align: center; border-bottom: 2px solid #dc3545; padding-bottom: 20px; margin-bottom: 30px; }
        .header h1 { color: #dc3545; margin: 0; }
        .alert-icon { font-size: 2em; margin-bottom: 10px; }
        .article { background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 6px; padding: 15px; margin-bottom: 20px; }
        .article h3 { margin: 0 0 10px 0; color: #721c24; }
        .article-meta { font-size: 0.9em; color: #721c24; margin-bottom: 10px; font-weight: bold; }
        .importance-badge { padding: 4px 12px; border-radius: 12px; font-size: 0.9em; font-weight: bold; background-color: #dc3545; color: white; }
        .footer { margin-top: 40px; text-align: center; font-size: 0.9em; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="alert-icon">🚨</div>
            <h1>{{ report_title }}</h1>
            <p><strong>{{ total_articles }}件の緊急記事</strong></p>
            <p>生成日時: {{ generated_at.strftime('%Y年%m月%d日 %H:%M:%S') }}</p>
        </div>
        
        {% for article in articles %}
        <div class="article">
            <h3>{{ article.translated_title or article.title }}</h3>
            <div class="article-meta">
                <span class="importance-badge">重要度: {{ article.importance_score or 'N/A' }}</span>
                {% if article.cvss_score %}
                <span class="importance-badge">CVSS: {{ article.cvss_score }}</span>
                {% endif %}
                <span>{{ article.source }}</span>
            </div>
            <p>{{ article.summary or (article.translated_content or article.content)[:300] + '...' if (article.translated_content or article.content) }}</p>
            {% if article.url %}
            <p><a href="{{ article.url }}" target="_blank" style="color: #721c24;">詳細を見る</a></p>
            {% endif %}
        </div>
        {% endfor %}
        
        <div class="footer">
            <p><strong>緊急対応が必要な可能性があります</strong></p>
            <p>このアラートは自動生成されました | News Delivery System</p>
        </div>
    </div>
</body>
</html>
        '''
        
        template = Template(template_str)
        return template.render(**data)
    
    def _generate_weekly_inline_template(self, **data) -> str:
        """インライン週次サマリーテンプレート"""
        template_str = '''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ report_title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }
        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        .header { border-bottom: 2px solid #28a745; padding-bottom: 20px; margin-bottom: 30px; }
        .header h1 { color: #28a745; margin: 0; }
        .summary-stats { background: #d4edda; padding: 20px; border-radius: 6px; margin-bottom: 30px; }
        .top-articles { margin-bottom: 30px; }
        .article { background: #f8f9fa; border-left: 4px solid #28a745; padding: 15px; margin-bottom: 10px; }
        .article h4 { margin: 0 0 5px 0; color: #155724; }
        .footer { margin-top: 40px; text-align: center; font-size: 0.9em; color: #6c757d; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ report_title }}</h1>
            <p>期間: {{ week_start.strftime('%Y年%m月%d日') }} - {{ week_end.strftime('%Y年%m月%d日') }}</p>
        </div>
        
        <div class="summary-stats">
            <h2>週次統計</h2>
            <p><strong>総記事数:</strong> {{ total_articles }}件</p>
            {% if statistics.peak_day %}
            <p><strong>最も記事が多かった日:</strong> {{ statistics.peak_day }}</p>
            {% endif %}
            <p><strong>活動日数:</strong> {{ statistics.total_days }}日</p>
        </div>
        
        <div class="top-articles">
            <h2>注目記事 TOP10</h2>
            {% for article in top_articles %}
            <div class="article">
                <h4>{{ article.translated_title or article.title }}</h4>
                <p><strong>重要度:</strong> {{ article.importance_score or 'N/A' }} | <strong>ソース:</strong> {{ article.source }}</p>
                <p>{{ article.summary[:150] + '...' if article.summary and article.summary|length > 150 else article.summary or '' }}</p>
            </div>
            {% endfor %}
        </div>
        
        <div class="footer">
            <p>週次サマリー | News Delivery System</p>
        </div>
    </div>
</body>
</html>
        '''
        
        template = Template(template_str)
        return template.render(**data)
    
    def _generate_error_report(self, error_message: str) -> str:
        """エラーレポート生成"""
        return f'''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>レポート生成エラー</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f8d7da; }}
        .error-container {{ background: white; padding: 30px; border-radius: 8px; border: 2px solid #dc3545; }}
        .error-header {{ color: #dc3545; text-align: center; }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-header">
            <h1>⚠️ レポート生成エラー</h1>
            <p>{error_message}</p>
            <p>システム管理者にお問い合わせください。</p>
            <p>生成時刻: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
        '''


# グローバルHTMLジェネレーターインスタンス
_html_generator_instance = None


def get_html_generator() -> HTMLReportGenerator:
    """グローバルHTMLジェネレーターインスタンス取得"""
    global _html_generator_instance
    if _html_generator_instance is None:
        _html_generator_instance = HTMLReportGenerator()
    return _html_generator_instance