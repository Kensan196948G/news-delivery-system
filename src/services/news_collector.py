"""
News Collection Service
ニュース収集サービス - 改善版（新しいcollectorsモジュール使用）
監視機能統合版
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..collectors import GNewsCollector, NewsAPICollector, NVDCollector
from ..models.article import Article
from ..models.database import Database
from ..utils.config import get_config
from ..utils.logger import get_performance_logger, setup_logger
from ..utils.monitoring_integration import (
    MonitoredCollectorMixin,
    get_health_checker,
    monitor_collection,
)


class NewsCollector:
    """統合ニュース収集サービス（監視機能付き）"""

    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = setup_logger(__name__)
        self.performance_logger = get_performance_logger(__name__)
        self.db = Database(self.config)

        # 健康チェッカー初期化
        self.health_checker = get_health_checker()

        # 新しいcollectorsモジュールのコレクターを初期化
        self.newsapi = (
            NewsAPICollector(self.config, self.logger)
            if self.config.is_service_enabled("newsapi")
            else None
        )

        # GNews is optional - disable if API key issues
        try:
            if self.config.is_service_enabled("gnews") and self.config.get_api_key(
                "gnews"
            ):
                self.gnews = GNewsCollector(self.config, self.logger)
                self.logger.info("GNews collector initialized successfully")
            else:
                self.gnews = None
                self.logger.info(
                    "GNews collector disabled - API key not available or service disabled"
                )
        except Exception as e:
            self.logger.warning(f"GNews collector initialization failed: {e}")
            self.gnews = None

        self.nvd = (
            NVDCollector(self.config, self.logger)
            if self.config.is_service_enabled("nvd")
            else None
        )

        # コレクターのヘルスチェック登録
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._register_collectors_for_monitoring())
        except RuntimeError:
            # No running event loop (e.g., during unit tests)
            self.logger.debug("No running event loop; skipping collector registration")

    async def _register_collectors_for_monitoring(self):
        """コレクターを監視対象に登録"""
        try:
            if self.newsapi:
                await self.health_checker.register_collector("newsapi", self.newsapi)
            if self.gnews:
                await self.health_checker.register_collector("gnews", self.gnews)
            if self.nvd:
                await self.health_checker.register_collector("nvd", self.nvd)
        except Exception as e:
            self.logger.warning(f"Failed to register collectors for monitoring: {e}")

    @monitor_collection
    async def collect_all_news(self) -> List[Article]:
        """全ソースからニュースを収集（監視付き）"""
        self.performance_logger.start_timer("collect_all_news")

        all_articles = []

        try:
            # Collect from different sources concurrently
            tasks = []

            # NewsAPI - Japanese general news and international tech/business
            if self.newsapi:
                tasks.append(
                    self.newsapi.collect(
                        category="general", country="jp", language="ja", page_size=30
                    )
                )
                tasks.append(
                    self.newsapi.collect(
                        category="technology", country="us", language="en", page_size=20
                    )
                )
                tasks.append(
                    self.newsapi.collect(
                        category="business", country="us", language="en", page_size=15
                    )
                )

            # GNews - Additional international news with focus on human rights
            if self.gnews:
                tasks.append(
                    self.gnews.collect(category="world", language="en", max_results=20)
                )
                tasks.append(self.gnews.collect_human_rights_news(max_results=15))
                tasks.append(self.gnews.collect_tech_news(max_results=20))

            # NVD - Security vulnerabilities
            if self.nvd:
                tasks.append(self.nvd.collect(days_back=7))

            # Execute all collection tasks
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, list):
                        all_articles.extend(result)
                    elif isinstance(result, Exception):
                        self.logger.error(f"Collection task failed: {result}")

            # Deduplicate articles
            all_articles = self._deduplicate_articles(all_articles)

            # Filter and sort by importance
            all_articles = self._filter_and_rank_articles(all_articles)

            self.logger.info(f"Total collected articles: {len(all_articles)}")

        except Exception as e:
            self.logger.error(f"Error in collect_all_news: {e}")

        finally:
            self.performance_logger.end_timer("collect_all_news")

        return all_articles

    async def collect_emergency_news(self) -> List[Article]:
        """緊急ニュースのみを収集"""
        try:
            articles = []

            # High severity vulnerabilities from NVD
            if self.nvd:
                vulns = await self.nvd.collect_critical_vulnerabilities(days_back=1)
                articles.extend(vulns)

            # Breaking news from NewsAPI
            if self.newsapi:
                breaking_news = await self.newsapi.collect(
                    category="general", country="jp", language="ja", page_size=10
                )
                articles.extend(breaking_news)

            return articles

        except Exception as e:
            self.logger.error(f"Error collecting emergency news: {e}")
            return []

    async def collect_by_category(
        self, category: str, max_articles: int = 50
    ) -> List[Article]:
        """カテゴリ別ニュース収集"""
        try:
            articles = []

            if category == "domestic_social" and self.newsapi:
                articles.extend(
                    await self.newsapi.collect(
                        category="general",
                        country="jp",
                        language="ja",
                        page_size=max_articles,
                    )
                )

            elif category == "international_social" and self.gnews:
                articles.extend(
                    await self.gnews.collect_human_rights_news(max_results=max_articles)
                )

            elif category == "tech" and self.gnews:
                articles.extend(
                    await self.gnews.collect_tech_news(max_results=max_articles)
                )

            elif category == "security" and self.nvd:
                articles.extend(await self.nvd.collect(days_back=14))

            elif category == "economy":
                tasks = []
                if self.newsapi:
                    tasks.append(
                        self.newsapi.collect(
                            category="business",
                            country="jp",
                            language="ja",
                            page_size=max_articles // 2,
                        )
                    )
                    tasks.append(
                        self.newsapi.collect(
                            category="business",
                            country="us",
                            language="en",
                            page_size=max_articles // 2,
                        )
                    )

                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, list):
                            articles.extend(result)

            return articles[:max_articles]

        except Exception as e:
            self.logger.error(f"Error collecting {category} news: {e}")
            return []

    def _deduplicate_articles(self, articles: List[Article]) -> List[Article]:
        """記事の重複を除去"""
        seen_urls = set()
        seen_titles = set()
        unique_articles = []

        for article in articles:
            url = article.url if hasattr(article, "url") else ""
            title = article.title if hasattr(article, "title") else ""

            # Create a normalized version for comparison
            normalized_title = title.lower().strip()

            if url in seen_urls or normalized_title in seen_titles:
                continue

            seen_urls.add(url)
            seen_titles.add(normalized_title)
            unique_articles.append(article)

        self.logger.info(
            f"Deduplication: {len(articles)} -> {len(unique_articles)} articles"
        )
        return unique_articles

    def _filter_and_rank_articles(self, articles: List[Article]) -> List[Article]:
        """記事のフィルタリングと重要度ランキング"""
        filtered_articles = []

        for article in articles:
            # Basic quality filters
            title = article.title if hasattr(article, "title") and article.title else ""
            content = (
                article.content
                if hasattr(article, "content") and article.content
                else ""
            )

            # Skip articles with insufficient content
            if not title or not content or len(title) < 10 or len(content) < 50:
                continue

            # Skip advertisements or promotional content
            if any(
                keyword in title.lower()
                for keyword in ["ad", "sponsored", "advertisement"]
            ):
                continue

            # Assign preliminary importance score
            importance_score = self._calculate_importance_score(article)
            if hasattr(article, "importance_score"):
                article.importance_score = importance_score
            else:
                article.importance_score = importance_score

            # Filter by minimum importance
            min_importance = self.config.get(
                "article_processing", "importance_threshold", default=3
            )
            if importance_score >= min_importance:
                filtered_articles.append(article)

        # Sort by importance score (descending)
        filtered_articles.sort(
            key=lambda x: getattr(x, "importance_score", 0), reverse=True
        )

        self.logger.info(f"Filtered articles: {len(filtered_articles)}")
        return filtered_articles

    def _calculate_importance_score(self, article) -> int:
        """記事の重要度スコア計算（1-10）"""
        score = 5  # Base score

        # Handle both Article dataclass and dictionary objects
        if hasattr(article, "title"):  # Article dataclass
            title = (article.title or "").lower()
            content = (article.content or "").lower()
            category = (
                str(article.category)
                if hasattr(article, "category") and article.category
                else ""
            )
            cvss_score = getattr(article, "cvss_score", 0) or 0
        else:  # Dictionary (fallback)
            title = article.get("title", "").lower()
            content = article.get("content", "").lower()
            category = article.get("category", "")
            cvss_score = article.get("cvss_score", 0)

        # Security vulnerabilities get high scores
        if cvss_score > 0:
            if cvss_score >= 9.0:
                score = 10
            elif cvss_score >= 7.0:
                score = 8
            else:
                score = 6

        # Technology and security keywords
        tech_keywords = [
            "ai",
            "artificial intelligence",
            "人工知能",
            "セキュリティ",
            "security",
            "vulnerability",
            "脆弱性",
            "breach",
            "hack",
            "cyber",
        ]
        for keyword in tech_keywords:
            if keyword in title or keyword in content:
                score += 1
                break

        # Breaking news indicators
        urgent_keywords = ["breaking", "速報", "urgent", "緊急", "alert", "critical"]
        for keyword in urgent_keywords:
            if keyword in title:
                score += 2
                break

        # Category-based scoring
        if "security" in category.lower():
            score += 2
        elif "tech" in category.lower():
            score += 1

        # Published time (recent news gets higher score)
        try:
            if hasattr(article, "published_at") and article.published_at:
                if isinstance(article.published_at, str):
                    published_at = datetime.fromisoformat(
                        article.published_at.replace("Z", "+00:00")
                    )
                else:
                    published_at = article.published_at

                hours_ago = (
                    datetime.now() - published_at.replace(tzinfo=None)
                ).total_seconds() / 3600
                if hours_ago < 6:
                    score += 1
        except:
            pass

        return min(max(score, 1), 10)  # Clamp between 1-10

    def get_collector_status(self) -> Dict[str, Any]:
        """全コレクターの状況を取得"""
        status = {"total_collectors": 0, "active_collectors": 0, "collectors": {}}

        collectors = [
            ("newsapi", self.newsapi),
            ("gnews", self.gnews),
            ("nvd", self.nvd),
        ]

        for name, collector in collectors:
            status["total_collectors"] += 1

            if collector:
                status["active_collectors"] += 1
                status["collectors"][name] = collector.get_service_status()
            else:
                status["collectors"][name] = {
                    "service": name,
                    "status": "disabled",
                    "reason": "Not configured or API key missing",
                }

        return status

    async def get_monitoring_status(self) -> Dict[str, Any]:
        """監視システム全体の状況を取得"""
        try:
            # 全コレクターのヘルスチェック
            health_status = await self.health_checker.check_all_collectors()

            # 個別コレクターの監視統計（MonitoredCollectorMixin使用時）
            collector_stats = {}
            for name, collector in [
                ("newsapi", self.newsapi),
                ("gnews", self.gnews),
                ("nvd", self.nvd),
            ]:
                if collector and hasattr(collector, "get_monitoring_stats"):
                    collector_stats[name] = collector.get_monitoring_stats()

            return {
                "health_status": health_status,
                "collector_monitoring_stats": collector_stats,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to get monitoring status: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
