#!/usr/bin/env python3
"""
News Delivery System - Main Entry Point
ニュース自動配信システム メインプログラム - CLAUDE.md仕様準拠

実行フロー制御とエラーハンドリング
"""

import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules according to CLAUDE.md specification
from collectors.newsapi_collector import NewsAPICollector
from collectors.nvd_collector import NVDCollector
from collectors.gnews_collector import GNewsCollector
from processors.translator import DeepLTranslator
from processors.analyzer import ClaudeAnalyzer
from processors.deduplicator import ArticleDeduplicator
from generators.html_generator import HTMLReportGenerator
from generators.pdf_generator import PDFReportGenerator
from notifiers.gmail_sender import GmailSender
from models.article import Article
from models.database import Database
from utils.config import ConfigManager
from utils.logger import setup_logger
from utils.cache_manager import CacheManager
from utils.monitoring_system import get_monitoring_system
from services.self_healing_system import get_self_healing_system


class NewsDeliverySystem:
    """ニュース自動配信システム - CLAUDE.md仕様準拠"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.logger = setup_logger(__name__)
        self.db = Database()
        self.cache_manager = CacheManager()
        self.test_delivery_mode = False  # テスト配信モード
        
        # Initialize monitoring and self-healing systems
        self.monitoring_system = get_monitoring_system()
        self.healing_system = get_self_healing_system()
        
        # Initialize collectors
        self.collectors = {}
        try:
            if self.config.get_api_key('newsapi'):
                self.collectors['newsapi'] = NewsAPICollector(self.config, self.logger)
                self.logger.info("NewsAPI collector initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize NewsAPI collector: {e}")
        
        try:
            if self.config.get_api_key('nvd'):
                self.collectors['nvd'] = NVDCollector(self.config, self.logger)
                self.logger.info("NVD collector initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize NVD collector: {e}")
        
        try:
            if self.config.get_api_key('gnews'):
                self.collectors['gnews'] = GNewsCollector(self.config, self.logger)
                self.logger.info("GNews collector initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize GNews collector: {e}")
        
        active_collectors = {k: v for k, v in self.collectors.items() if v is not None}
        if not active_collectors:
            self.logger.warning("No collectors initialized successfully - running in test mode")
        else:
            self.logger.info(f"Successfully initialized {len(active_collectors)} collectors: {list(active_collectors.keys())}")
        
        # Initialize processors
        self.translator = DeepLTranslator(self.config)
        self.analyzer = ClaudeAnalyzer(self.config)
        self.deduplicator = ArticleDeduplicator()
        
        # Initialize generators
        self.html_generator = HTMLReportGenerator(self.config)
        self.pdf_generator = PDFReportGenerator(self.config)
        
        # Initialize notifier
        self.gmail_sender = GmailSender(self.config)
        
        self.logger.info("News Delivery System initialized - CLAUDE.md specification compliant")
    
    async def run(self):
        """メイン処理フロー - CLAUDE.md仕様"""
        try:
            self.logger.info("Starting news delivery system main workflow")
            start_time = datetime.now()
            
            # 監視・自己修復システム開始
            await self.monitoring_system.start_monitoring()
            await self.healing_system.start_healing_loop()
            
            # メイン処理ブロック
            # 1. ニュース収集
            self.logger.info("Step 1: Collecting news from multiple sources")
            articles = await self.collect_news()
            self.logger.info(f"Collected {len(articles)} total articles")
            
            if not articles:
                self.logger.warning("No articles collected. Exiting.")
                return
            
            # 2. 重複除去
            self.logger.info("Step 2: Removing duplicate articles")
            unique_articles = await self.deduplicate(articles)
            self.logger.info(f"After deduplication: {len(unique_articles)} unique articles")
            
            # 3. 翻訳処理
            self.logger.info("Step 3: Translating foreign articles")
            translated_articles = await self.translate(unique_articles)
            
            # 4. AI分析・要約
            self.logger.info("Step 4: AI analysis and summarization")
            analyzed_articles = await self.analyze(translated_articles)
            
            # 5. レポート生成
            self.logger.info("Step 5: Generating HTML and PDF reports")
            report_paths = await self.generate_reports(analyzed_articles)
        
            # 6. メール配信
            self.logger.info("Step 6: Sending email notifications")
            await self.send_notifications(report_paths, analyzed_articles)
            
            # 7. データ保存
            self.logger.info("Step 7: Saving data to database")
            await self.save_data(analyzed_articles)
            
            # 実行時間計算
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"News delivery system completed successfully in {execution_time:.2f} seconds")
        
            # 緊急アラートチェック
            await self.check_emergency_alerts(analyzed_articles)
            
        except Exception as e:
            self.logger.error(f"System error: {str(e)}", exc_info=True)
            
            # エラーを監視システムで分類・処理
            error_category = await self.monitoring_system.handle_error_with_classification(e, "main_workflow")
            
            # エラー通知
            await self.send_error_notification(e)
            
            raise
            
        finally:
            # 監視・自己修復システム停止
            try:
                await self.healing_system.stop_healing_loop()
                await self.monitoring_system.stop_monitoring()
            except:
                pass
    
    async def collect_news(self) -> List[Article]:
        """ニュース収集 - CLAUDE.md仕様準拠"""
        try:
            self.logger.info(f"Starting news collection with config type: {type(self.config)}")
            all_articles = []
            collection_tasks = []
            
            # NVDコレクターが失敗してもNewsAPIとGNewsがあれば継続
            active_collectors = {k: v for k, v in self.collectors.items() if v is not None}
            if not active_collectors:
                self.logger.info("No API collectors available - generating test articles")
                return self._generate_test_articles()
            
            # カテゴリ別収集設定 - CLAUDE.md準拠
            if self.config is None:
                self.logger.error("Configuration not loaded properly")
                return []
            
            try:
                collection_config = self.config.get('collection')
                if not collection_config:
                    self.logger.warning("Collection config is None - using test articles")
                    return self._generate_test_articles()
                    
                categories = collection_config.get('categories', {})
                self.logger.info(f"Found {len(categories)} categories: {list(categories.keys())}")
            except Exception as e:
                self.logger.error(f"Failed to get categories from config: {e} - using test articles")
                return self._generate_test_articles()
            
            for category_name, category_config in categories.items():
                if not category_config.get('enabled', True):
                    continue
                
                count = category_config.get('count', 10)
                priority = category_config.get('priority', 5)
                
                self.logger.debug(f"Collecting {category_name}: {count} articles, priority {priority}")
                
                # Dual-source collection strategy (NewsAPI + GNews)
                if category_name in ['domestic_social', 'domestic_economy']:
                    # 国内ニュースはNewsAPIが強い
                    task = self._collect_newsapi_category(category_name, count, 'jp', 'ja')
                    collection_tasks.append(task)
                elif category_name in ['international_social', 'international_economy']:
                    # 国際ニュースは両方のソースを使用（多様性向上）
                    keywords = category_config.get('keywords', [])
                    query = ' OR '.join(keywords) if keywords else self._get_default_query(category_name)
                    
                    # NewsAPIとGNewsから半分ずつ収集
                    newsapi_count = count // 2
                    gnews_count = count - newsapi_count
                    
                    newsapi_task = self._collect_newsapi_everything(query, newsapi_count, 'en')
                    gnews_task = self._collect_gnews_category(category_name, gnews_count, keywords)
                    
                    collection_tasks.extend([newsapi_task, gnews_task])
                elif category_name == 'tech':
                    # 技術ニュースも両方のソースで多様性確保
                    keywords = category_config.get('keywords', [])
                    query = ' OR '.join(keywords) if keywords else self._get_default_query(category_name)
                    
                    newsapi_count = count // 2
                    gnews_count = count - newsapi_count
                    
                    newsapi_task = self._collect_newsapi_everything(query, newsapi_count, 'en')
                    gnews_task = self._collect_gnews_tech(gnews_count, keywords)
                    
                    collection_tasks.extend([newsapi_task, gnews_task])
                elif category_name == 'security':
                    # セキュリティは現状維持（NVD + NewsAPI）
                    task = self._collect_nvd_vulnerabilities(count, category_config.get('alert_threshold', 9.0))
                    collection_tasks.append(task)
                else:
                    continue
            
            # 並行実行
            results = await asyncio.gather(*collection_tasks, return_exceptions=True)
            
            # 結果をマージ
            for result in results:
                if isinstance(result, list):
                    all_articles.extend(result)
                elif isinstance(result, Exception):
                    self.logger.error(f"Collection task failed: {result}")
            
            return all_articles
            
        except Exception as e:
            self.logger.error(f"News collection failed: {e}")
            # エラー分類・処理
            await self.monitoring_system.handle_error_with_classification(e, "news_collection")
            return []
    
    async def _collect_newsapi_category(self, category: str, count: int, country: str, language: str) -> List[Article]:
        """NewsAPI カテゴリ別収集"""
        try:
            async with self.collectors['newsapi'] as collector:
                return await collector.collect(
                    category=category.split('_')[1] if '_' in category else category,
                    country=country,
                    language=language,
                    page_size=count
                )
        except Exception as e:
            self.logger.error(f"NewsAPI collection failed for {category}: {e}")
            return []
    
    async def _collect_newsapi_everything(self, query: str, count: int, language: str) -> List[Article]:
        """NewsAPI Everything検索"""
        try:
            async with self.collectors['newsapi'] as collector:
                return await collector.collect_everything(
                    query=query,
                    language=language,
                    page_size=count
                )
        except Exception as e:
            self.logger.error(f"NewsAPI Everything search failed for '{query}': {e}")
            return []
    
    async def _collect_nvd_vulnerabilities(self, count: int, cvss_threshold: float) -> List[Article]:
        """NVD脆弱性情報収集"""
        try:
            async with self.collectors['nvd'] as collector:
                if cvss_threshold >= 9.0:
                    return await collector.collect_critical_vulnerabilities()
                else:
                    return await collector.collect_recent_high_vulnerabilities()
        except Exception as e:
            self.logger.error(f"NVD collection failed: {e}")
            return []
    
    async def _collect_gnews_category(self, category: str, count: int, keywords: List[str] = None) -> List[Article]:
        """GNews カテゴリ別収集"""
        try:
            async with self.collectors['gnews'] as collector:
                if category == 'international_social':
                    # 人権関連キーワード使用
                    query = ' OR '.join(keywords) if keywords else 'human rights OR social justice OR migration'
                    return await collector.collect_by_query(query, count, language='en')
                elif category == 'international_economy':
                    query = 'global economy OR international trade OR world market OR economic crisis'
                    return await collector.collect_by_query(query, count, language='en')
                else:
                    return await collector.collect_by_category('general', count, language='en')
        except Exception as e:
            self.logger.error(f"GNews collection failed for {category}: {e}")
            return []
    
    async def _collect_gnews_tech(self, count: int, keywords: List[str] = None) -> List[Article]:
        """GNews 技術ニュース収集"""
        try:
            async with self.collectors['gnews'] as collector:
                # 技術関連の多様なキーワード
                tech_queries = [
                    'artificial intelligence OR machine learning',
                    'cloud computing OR data science',
                    'blockchain OR cryptocurrency',
                    'cybersecurity OR data privacy',
                    'software development OR programming'
                ]
                
                # 複数クエリから記事を収集して多様性確保
                all_articles = []
                per_query_count = max(1, count // len(tech_queries))
                
                for query in tech_queries[:3]:  # 上位3つのクエリを使用
                    articles = await collector.collect_by_query(query, per_query_count, language='en')
                    all_articles.extend(articles)
                
                return all_articles[:count]  # 指定数に調整
                
        except Exception as e:
            self.logger.error(f"GNews tech collection failed: {e}")
            return []
    
    def _get_default_query(self, category: str) -> str:
        """デフォルトクエリ生成"""
        queries = {
            'international_social': 'human rights OR social justice OR migration',
            'international_economy': 'economy OR market OR trade OR inflation',
            'tech': 'artificial intelligence OR machine learning OR cloud computing'
        }
        return queries.get(category, category)
    
    async def deduplicate(self, articles: List[Article]) -> List[Article]:
        """重複除去"""
        try:
            return await self.deduplicator.remove_duplicates(articles)
        except Exception as e:
            self.logger.error(f"Deduplication failed: {e}")
            return articles
    
    async def translate(self, articles: List[Article]) -> List[Article]:
        """翻訳処理 - CLAUDE.md仕様準拠"""
        try:
            return await self.translator.translate_batch(articles)
        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            # エラー分類・処理
            await self.monitoring_system.handle_error_with_classification(e, "translation")
            return articles
    
    async def analyze(self, articles: List[Article]) -> List[Article]:
        """AI分析・要約 - CLAUDE.md仕様準拠"""
        try:
            # 重要度で優先順位付け - 上位20件のみClaude分析
            prioritized_articles = sorted(
                articles,
                key=lambda x: getattr(x, 'importance_score', 5),
                reverse=True
            )
            
            high_priority_articles = prioritized_articles[:20]
            remaining_articles = prioritized_articles[20:]
            
            # Claude分析実行
            analyzed_articles = await self.analyzer.analyze_batch(high_priority_articles)
            
            # 残りは簡易分析
            for article in remaining_articles:
                article.importance_score = getattr(article, 'importance_score', 5)
                article.summary = (getattr(article, 'translated_content', '') or 
                                 getattr(article, 'content', ''))[:200] + '...'
                article.keywords = []
                article.sentiment = 'neutral'
            
            return analyzed_articles + remaining_articles
            
        except Exception as e:
            self.logger.error(f"AI analysis failed: {e}")
            # エラー分類・処理
            await self.monitoring_system.handle_error_with_classification(e, "ai_analysis")
            return articles
    
    async def generate_reports(self, articles: List[Article]) -> Dict[str, str]:
        """レポート生成 - CLAUDE.md仕様準拠"""
        try:
            report_paths = {}
            
            # HTML生成
            html_content = self.html_generator.generate_daily_report(articles)
            
            # HTMLファイル保存
            html_path = self._save_html_report(html_content)
            if html_path:
                report_paths['html'] = html_path
            
            # PDF生成
            pdf_path = self.pdf_generator.generate_daily_report(articles)
            if pdf_path:
                report_paths['pdf'] = pdf_path
            
            return report_paths
            
        except Exception as e:
            self.logger.error(f"Report generation failed: {e}")
            # エラー分類・処理
            await self.monitoring_system.handle_error_with_classification(e, "report_generation")
            return {}
    
    def _save_html_report(self, html_content: str) -> Optional[str]:
        """HTMLレポート保存"""
        try:
            date_str = datetime.now().strftime('%Y%m%d')
            html_filename = f"daily_news_report_{date_str}.html"
            
            reports_dir = Path(self.config.get('paths.data_root', '/tmp')) / 'reports' / 'daily'
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            html_path = reports_dir / html_filename
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.debug(f"HTML report saved: {html_path}")
            return str(html_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save HTML report: {e}")
            return None
    
    async def send_notifications(self, report_paths: Dict[str, str], articles: List[Article]):
        """メール配信 - CLAUDE.md仕様準拠"""
        try:
            # HTML内容読み込み
            html_content = ""
            if 'html' in report_paths and os.path.exists(report_paths['html']):
                with open(report_paths['html'], 'r', encoding='utf-8') as f:
                    html_content = f.read()
            else:
                # フォールバック: HTMLジェネレーターで再生成
                html_content = self.html_generator.generate_daily_report(articles)
            
            # テスト配信モードではメール送信をスキップ
            if self.test_delivery_mode:
                self.logger.info("TEST MODE: Skipping email delivery - HTML report saved only")
                print(f"📧 テスト配信モード: HTMLレポートが保存されました")
                if 'html' in report_paths:
                    print(f"   HTMLファイル: {report_paths['html']}")
                if 'pdf' in report_paths:
                    print(f"   PDFファイル: {report_paths['pdf']}")
                return
            
            # Gmail送信
            success = await self.gmail_sender.send_daily_report(
                html_content=html_content,
                pdf_path=report_paths.get('pdf'),
                articles=articles
            )
            
            if success:
                self.logger.info("Daily report sent successfully")
            else:
                self.logger.error("Failed to send daily report")
            
        except Exception as e:
            self.logger.error(f"Email notification failed: {e}")
            # エラー分類・処理
            await self.monitoring_system.handle_error_with_classification(e, "email_notification")
    
    async def save_data(self, articles: List[Article]):
        """データ保存 - CLAUDE.md仕様準拠"""
        try:
            # 記事をデータベースに保存
            saved_count = self.db.save_articles(articles)
            
            # 配信履歴をログ
            recipients = self.config.get('delivery.recipients', [])
            for recipient in recipients:
                self.db.log_delivery(
                    delivery_type='scheduled',
                    recipient_email=recipient,
                    subject=f'ニュース配信レポート - {datetime.now().strftime("%Y年%m月%d日")}',
                    article_count=len(articles),
                    categories=[str(getattr(a, 'category', 'unknown')) for a in articles],
                    status='sent'
                )
            
            self.logger.info(f"Saved {saved_count} articles and logged delivery")
            
        except Exception as e:
            self.logger.error(f"Data saving failed: {e}")
            # エラー分類・処理
            await self.monitoring_system.handle_error_with_classification(e, "data_saving")
    
    async def check_emergency_alerts(self, articles: List[Article]):
        """緊急アラートチェック - CLAUDE.md仕様準拠"""
        try:
            # 緊急記事フィルタ（重要度10またはCVSS 9.0以上）
            emergency_articles = [
                article for article in articles
                if (getattr(article, 'importance_score', 0) >= 10 or 
                    getattr(article, 'cvss_score', 0) >= 9.0)
            ]
            
            if not emergency_articles:
                return
            
            self.logger.warning(f"Found {len(emergency_articles)} emergency articles - sending alert")
            
            # 緊急レポート生成
            emergency_html = self.html_generator.generate_emergency_report(emergency_articles)
            
            # 緊急メール送信
            success = await self.gmail_sender.send_emergency_alert(
                html_content=emergency_html,
                articles=emergency_articles
            )
            
            # 緊急配信ログ
            if success:
                recipients = self.config.get('delivery.recipients', [])
                for recipient in recipients:
                    self.db.log_delivery(
                        delivery_type='urgent',
                        recipient_email=recipient,
                        subject=f'緊急ニュースアラート - {len(emergency_articles)}件',
                        article_count=len(emergency_articles),
                        status='sent'
                    )
            
        except Exception as e:
            self.logger.error(f"Emergency alert check failed: {e}")
    
    async def send_error_notification(self, error: Exception):
        """エラー通知 - CLAUDE.md仕様準拠"""
        try:
            subject = f"[緊急] ニュース配信システムエラー: {error.__class__.__name__}"
            error_html = f"""
            <!DOCTYPE html>
            <html lang="ja">
            <head>
                <meta charset="UTF-8">
                <title>システムエラー</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8d7da; }}
                    .container {{ background: white; padding: 20px; border: 2px solid #dc3545; border-radius: 8px; }}
                    .error-header {{ color: #dc3545; text-align: center; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="error-header">
                        <h1>⚠️ システムエラー発生</h1>
                        <h2>{error.__class__.__name__}</h2>
                        <p><strong>エラーメッセージ:</strong> {str(error)}</p>
                        <p><strong>発生時刻:</strong> {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
                        <p>詳細はシステムログを確認してください。</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # エラーメール送信
            admin_emails = self.config.get('delivery.recipients', [])
            for email in admin_emails:
                try:
                    await self.gmail_sender._send_email(
                        recipients=[email],
                        subject=subject,
                        html_content=error_html,
                        email_type='error',
                        high_priority=True
                    )
                except:
                    pass  # エラー通知の送信エラーは無視
            
        except Exception as e:
            self.logger.error(f"Error notification failed: {e}")
    
    def _generate_test_articles(self) -> List[Article]:
        """テスト用のサンプル記事生成"""
        from datetime import datetime, timedelta
        
        test_articles = []
        
        # 国内社会ニュース（サンプル）
        article1 = Article(
            url="https://example.com/news/1",
            title="東京都で新しい防災訓練が実施される"
        )
        article1.description = "東京都は市民参加型の大規模防災訓練を実施し、約1万人が参加した。"
        article1.content = "東京都では本日、大規模な防災訓練が都内各地で実施され、市民約1万人が参加しました。この訓練は首都直下地震を想定したもので、避難誘導や救助活動の手順を確認しました。参加者からは「実際の災害時に役立つ」との声が聞かれました。"
        article1.source_name = "テストニュース"
        article1.published_at = datetime.now() - timedelta(hours=2)
        article1.category = "domestic_social"
        article1.importance_score = 7
        article1.keywords = ["防災", "訓練", "東京都", "地震", "避難"]
        article1.sentiment = "neutral"
        test_articles.append(article1)
        
        # 国際社会ニュース（サンプル）
        article2 = Article(
            url="https://example.com/news/2",
            title="Global Climate Summit Reaches Historic Agreement"
        )
        article2.translated_title = "国際気候サミットが歴史的合意に到達"
        article2.description = "World leaders agree on unprecedented climate action measures."
        article2.translated_content = "世界各国の首脳が気候変動対策について画期的な合意に達しました。この合意には温室効果ガスの大幅削減目標と、発展途上国への支援策が含まれています。"
        article2.content = "World leaders have reached a groundbreaking agreement on climate action at the Global Climate Summit. The agreement includes ambitious greenhouse gas reduction targets and support measures for developing countries."
        article2.source_name = "Global News Test"
        article2.published_at = datetime.now() - timedelta(hours=3)
        article2.category = "international_social"
        article2.importance_score = 9
        article2.keywords = ["climate", "summit", "environment", "agreement", "sustainability"]
        article2.sentiment = "positive"
        test_articles.append(article2)
        
        # ITニュース（サンプル）
        article3 = Article(
            url="https://example.com/news/3",
            title="Revolutionary AI Breakthrough in Medical Diagnosis"
        )
        article3.translated_title = "医療診断における革新的AI技術の突破口"
        article3.description = "New AI system shows 95% accuracy in early disease detection."
        article3.translated_content = "新しいAIシステムが早期疾患発見において95%の精度を実現しました。この技術により、従来は発見困難だった病気の早期診断が可能になると期待されています。医療従事者からは「医療の未来を変える技術」として高く評価されています。"
        article3.content = "A new AI system has achieved 95% accuracy in early disease detection, potentially revolutionizing medical diagnosis. The technology enables early detection of diseases that were previously difficult to diagnose."
        article3.source_name = "Tech News Today"
        article3.published_at = datetime.now() - timedelta(hours=1)
        article3.category = "tech"
        article3.importance_score = 8
        article3.keywords = ["AI", "medical", "diagnosis", "technology", "healthcare"]
        article3.sentiment = "positive"
        test_articles.append(article3)
        
        # セキュリティニュース（サンプル）
        article4 = Article(
            url="https://example.com/news/4",
            title="Critical Security Vulnerability Discovered in Popular Software"
        )
        article4.translated_title = "人気ソフトウェアで重大なセキュリティ脆弱性が発見"
        article4.description = "A high-severity vulnerability affects millions of users worldwide."
        article4.translated_content = "世界中で数百万人のユーザーに影響する高重要度の脆弱性が発見されました。この脆弱性により、攻撃者がシステムに不正アクセスする可能性があります。開発会社は緊急パッチの提供を開始しており、ユーザーに早急なアップデートを呼びかけています。"
        article4.content = "A high-severity vulnerability has been discovered that affects millions of users worldwide. The vulnerability could allow attackers to gain unauthorized access to systems."
        article4.source_name = "Security Alert"
        article4.published_at = datetime.now() - timedelta(minutes=30)
        article4.category = "security"
        article4.importance_score = 10
        article4.cvss_score = 9.2
        article4.keywords = ["security", "vulnerability", "software", "patch", "cyber"]
        article4.sentiment = "negative"
        test_articles.append(article4)
        
        # 経済ニュース（サンプル）
        article5 = Article(
            url="https://example.com/news/5",
            title="日本の新興企業が画期的な技術で海外進出"
        )
        article5.description = "革新的なテクノロジーを武器に、グローバル市場への展開を開始"
        article5.content = "日本の新興テクノロジー企業が開発した革新的な技術が国際的に注目され、アメリカとヨーロッパ市場への本格進出を開始しました。この技術により、従来の製品コストを50%削減できると期待されています。"
        article5.source_name = "経済新聞"
        article5.published_at = datetime.now() - timedelta(hours=4)
        article5.category = "domestic_economy"
        article5.importance_score = 6
        article5.keywords = ["新興企業", "技術", "海外進出", "革新", "コスト削減"]
        article5.sentiment = "positive"
        test_articles.append(article5)
        
        self.logger.info(f"Generated {len(test_articles)} test articles")
        return test_articles


def main():
    """メインエントリーポイント - CLAUDE.md仕様準拠"""
    import argparse
    
    parser = argparse.ArgumentParser(description='News Delivery System - CLAUDE.md仕様準拠')
    parser.add_argument('--mode', choices=['daily', 'emergency', 'test'],
                       default='daily', help='実行モード')
    parser.add_argument('--config', help='設定ファイルパス')
    parser.add_argument('--debug', action='store_true', help='デバッグモード')
    parser.add_argument('--test-delivery', action='store_true', help='テスト配信（メール送信なし）')
    
    args = parser.parse_args()
    
    # ログレベル設定
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        system = NewsDeliverySystem()
        
        # テスト配信フラグを設定
        if args.test_delivery:
            system.test_delivery_mode = True
        
        if args.mode == 'daily' or args.test_delivery:
            # 通常の日次処理またはテスト配信
            asyncio.run(system.run())
        elif args.mode == 'emergency':
            # 緊急チェックのみ
            print("Emergency mode not implemented in main workflow")
        elif args.mode == 'test':
            # テストモード
            print("News Delivery System - CLAUDE.md specification compliant")
            print("System initialized successfully")
            print(f"Configuration loaded: {getattr(system.config, 'config_path', 'N/A')}")
            print(f"Database path: {getattr(system.db, 'db_path', 'N/A')}")
            
    except KeyboardInterrupt:
        print("\n処理がユーザーによって中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"致命的エラー: {str(e)}")
        logging.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()