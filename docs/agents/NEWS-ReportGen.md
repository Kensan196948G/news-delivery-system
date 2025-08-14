# NEWS-ReportGen - レポート生成エージェント

## エージェント概要
ニュース配信システムのHTML/PDF レポート生成、メール配信用コンテンツ作成を専門とするエージェント。

## 役割と責任
- HTMLレポート生成
- PDFレポート作成
- メール配信用コンテンツ作成
- レポートテンプレート管理
- 可視化・グラフ生成

## 主要業務

### HTMLレポート生成
```python
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import os

class HTMLReportGenerator:
    def __init__(self, template_dir: str):
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.template = self.env.get_template('email_template.html')
        
    async def generate_daily_report(
        self, 
        articles: List[Article], 
        date: datetime,
        stats: Dict
    ) -> str:
        """日次レポート生成"""
        # カテゴリ別記事分類
        categorized = self._categorize_articles(articles)
        
        # 緊急アラート抽出
        alerts = self._extract_alerts(articles)
        
        # 統計情報生成
        summary_stats = self._generate_summary_stats(articles, stats)
        
        # テンプレートレンダリング
        html = self.template.render(
            report_date=date.strftime('%Y年%m月%d日 %A'),
            total_articles=len(articles),
            categories=categorized,
            alerts=alerts,
            statistics=summary_stats,
            generated_at=datetime.now(),
            system_status=self._get_system_status()
        )
        
        return html
    
    def _categorize_articles(self, articles: List[Article]) -> Dict[str, List[Article]]:
        """カテゴリ別記事整理"""
        categories = {
            '🚨 緊急アラート': [],
            '🏠 国内社会': [],
            '🌏 国際社会': [],
            '💹 経済・市場': [],
            '💻 IT・AI': [],
            '🔒 セキュリティ': []
        }
        
        for article in articles:
            # 緊急度判定
            if article.importance_score >= 10 or (hasattr(article, 'cvss_score') and article.cvss_score >= 9.0):
                categories['🚨 緊急アラート'].append(article)
                continue
            
            # カテゴリ分類
            category_map = {
                'domestic_social': '🏠 国内社会',
                'international_social': '🌏 国際社会',
                'economy': '💹 経済・市場',
                'tech': '💻 IT・AI',
                'security': '🔒 セキュリティ'
            }
            
            category = category_map.get(article.category, '🏠 国内社会')
            categories[category].append(article)
        
        # 各カテゴリ内で重要度順ソート
        for cat in categories:
            categories[cat].sort(key=lambda x: x.importance_score or 5, reverse=True)
            
        return categories
```

### PDF生成
```python
import pdfkit
from weasyprint import HTML, CSS

class PDFReportGenerator:
    def __init__(self):
        self.pdf_options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'enable-local-file-access': None
        }
        
    async def generate_pdf_from_html(
        self, 
        html_content: str, 
        output_path: str,
        css_styles: Optional[str] = None
    ) -> bool:
        """HTML から PDF 生成"""
        try:
            # CSS スタイル適用
            if css_styles:
                html_with_styles = f"<style>{css_styles}</style>{html_content}"
            else:
                html_with_styles = self._apply_default_pdf_styles(html_content)
            
            # WeasyPrint での PDF 生成
            document = HTML(string=html_with_styles)
            document.write_pdf(output_path)
            
            return os.path.exists(output_path)
            
        except Exception as e:
            self.logger.error(f"PDF generation error: {str(e)}")
            return False
    
    def _apply_default_pdf_styles(self, html: str) -> str:
        """PDF用デフォルトスタイル適用"""
        pdf_css = """
        <style>
        body { font-family: 'Noto Sans JP', sans-serif; font-size: 12px; line-height: 1.6; }
        .header { background: #2c3e50; color: white; padding: 20px; margin-bottom: 20px; }
        .category { margin-bottom: 30px; }
        .category h2 { color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .article { margin-bottom: 20px; padding: 15px; border-left: 3px solid #3498db; background: #f8f9fa; }
        .importance-10 { border-left-color: #e74c3c; background: #fdf2f2; }
        .importance-9 { border-left-color: #f39c12; background: #fef9e7; }
        .metadata { font-size: 10px; color: #7f8c8d; margin-top: 10px; }
        @page { margin: 2cm; }
        </style>
        """
        return pdf_css + html
```

### 可視化・グラフ生成
```python
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64

class VisualizationGenerator:
    def __init__(self):
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
    def generate_category_distribution_chart(self, articles: List[Article]) -> str:
        """カテゴリ分布グラフ生成"""
        category_counts = {}
        for article in articles:
            category_counts[article.category] = category_counts.get(article.category, 0) + 1
        
        fig, ax = plt.subplots(figsize=(10, 6))
        categories = list(category_counts.keys())
        counts = list(category_counts.values())
        
        bars = ax.bar(categories, counts, color=sns.color_palette("husl", len(categories)))
        ax.set_title('カテゴリ別記事数分布', fontsize=14, fontweight='bold')
        ax.set_ylabel('記事数')
        
        # 値をバーの上に表示
        for bar, count in zip(bars, counts):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                   str(count), ha='center', va='bottom')
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Base64エンコードして返す
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{image_base64}"
    
    def generate_importance_distribution(self, articles: List[Article]) -> str:
        """重要度分布ヒストグラム"""
        importance_scores = [article.importance_score or 5 for article in articles]
        
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(importance_scores, bins=10, alpha=0.7, color='skyblue', edgecolor='black')
        ax.set_title('記事重要度分布', fontsize=14, fontweight='bold')
        ax.set_xlabel('重要度スコア')
        ax.set_ylabel('記事数')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{image_base64}"
```

## 使用する技術・ツール
- **テンプレート**: Jinja2
- **PDF生成**: WeasyPrint, pdfkit
- **可視化**: matplotlib, seaborn
- **HTML/CSS**: Bootstrap, Custom CSS
- **画像処理**: PIL, base64
- **フォント**: Noto Sans JP

## 連携するエージェント
- **NEWS-DevUI**: UIテンプレート連携
- **NEWS-CSVHandler**: データ統計連携
- **NEWS-Analyzer**: 分析結果表示
- **NEWS-Monitor**: システム状況表示
- **NEWS-Scheduler**: 配信スケジュール表示

## KPI目標
- **HTML生成時間**: 5秒以内
- **PDF生成時間**: 10秒以内
- **レポート品質**: 4.8/5以上
- **テンプレート再利用率**: 90%以上
- **エラー率**: 0.1%未満

## レポート種類

### 日次レポート
- 新着記事一覧
- カテゴリ別サマリー
- 重要アラート
- システム状況

### 週次レポート
- 週間トレンド分析
- カテゴリ別統計
- 配信効果分析
- パフォーマンス報告

### 月次レポート
- 月間統計サマリー
- 利用状況分析
- 改善提案
- ROI分析

## カスタマイズ機能
- テンプレート動的選択
- スタイル設定変更
- レポート項目制御
- 多言語対応

## 品質管理
- テンプレート検証
- レンダリング品質チェック
- PDF品質確認
- パフォーマンス監視

## 成果物
- HTMLレポートテンプレート
- PDF生成システム
- 可視化チャート
- カスタマイズ設定
- レポート品質メトリクス