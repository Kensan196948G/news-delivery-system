"""
Collection Analytics and Statistics Module
ニュース収集分析・統計モジュール
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import statistics

from models.article import Article, ArticleCategory, ArticleLanguage
from utils.cache_manager import get_cache_manager
from utils.config import get_config


@dataclass
class CollectionMetrics:
    """収集メトリクス"""
    timestamp: str
    total_articles: int
    articles_by_source: Dict[str, int]
    articles_by_category: Dict[str, int]
    articles_by_language: Dict[str, int]
    processing_time: float
    success_rate: float
    duplicate_rate: float
    average_importance: float
    urgent_articles: int
    errors: List[str]


@dataclass
class PerformanceMetrics:
    """パフォーマンスメトリクス"""
    collector_name: str
    requests_made: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    cache_hit_rate: float
    articles_per_request: float
    error_rate: float
    last_collection_time: str


@dataclass
class QualityMetrics:
    """品質メトリクス"""
    source_diversity: float
    content_quality_score: float
    translation_coverage: float
    urgency_detection_rate: float
    category_distribution_balance: float
    temporal_coverage: float


class CollectionAnalytics:
    """ニュース収集分析クラス"""
    
    def __init__(self):
        self.config = get_config()
        self.cache = get_cache_manager()
        self.logger = logging.getLogger(__name__)
        
        # メトリクス保存設定
        self.metrics_retention_days = 30
        self.detailed_metrics_retention_hours = 72
        
        # 分析閾値
        self.quality_thresholds = {
            'min_sources': 3,
            'min_categories': 4,
            'min_success_rate': 80.0,
            'max_duplicate_rate': 20.0,
            'min_content_quality': 70.0,
            'min_diversity_score': 60.0
        }
    
    def record_collection_session(self, articles: List[Article], 
                                processing_time: float,
                                collection_results: List[Any],
                                duplicate_info: Dict[str, Any]) -> CollectionMetrics:
        """収集セッションの記録"""
        timestamp = datetime.now().isoformat()
        
        try:
            # 基本統計計算
            basic_stats = self._calculate_basic_statistics(articles)
            
            # パフォーマンス統計
            perf_stats = self._calculate_performance_statistics(collection_results)
            
            # エラー集計
            errors = [r.error_message for r in collection_results if hasattr(r, 'error_message') and r.error_message]
            
            metrics = CollectionMetrics(
                timestamp=timestamp,
                total_articles=len(articles),
                articles_by_source=basic_stats['by_source'],
                articles_by_category=basic_stats['by_category'],
                articles_by_language=basic_stats['by_language'],
                processing_time=processing_time,
                success_rate=perf_stats['success_rate'],
                duplicate_rate=duplicate_info.get('duplicate_rate', 0.0),
                average_importance=basic_stats['avg_importance'],
                urgent_articles=basic_stats['urgent_count'],
                errors=errors
            )
            
            # キャッシュに保存
            self._store_metrics(metrics)
            
            # アラート条件チェック
            self._check_alert_conditions(metrics)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to record collection session: {e}")
            return CollectionMetrics(
                timestamp=timestamp,
                total_articles=len(articles),
                articles_by_source={},
                articles_by_category={},
                articles_by_language={},
                processing_time=processing_time,
                success_rate=0.0,
                duplicate_rate=0.0,
                average_importance=0.0,
                urgent_articles=0,
                errors=[str(e)]
            )
    
    def analyze_collector_performance(self, collector_stats: Dict[str, Any]) -> List[PerformanceMetrics]:
        """収集器パフォーマンス分析"""
        performance_metrics = []
        
        for collector_name, stats in collector_stats.items():
            try:
                if isinstance(stats, dict) and 'requests_made' in stats:
                    metrics = PerformanceMetrics(
                        collector_name=collector_name,
                        requests_made=stats.get('requests_made', 0),
                        successful_requests=stats.get('successful_requests', 0),
                        failed_requests=stats.get('failed_requests', 0),
                        average_response_time=stats.get('average_response_time', 0.0),
                        cache_hit_rate=self._calculate_cache_hit_rate(stats),
                        articles_per_request=stats.get('articles_per_request', 0.0),
                        error_rate=self._calculate_error_rate(stats),
                        last_collection_time=stats.get('last_collection_time', '')
                    )
                    performance_metrics.append(metrics)
                    
            except Exception as e:
                self.logger.warning(f"Failed to analyze performance for {collector_name}: {e}")
        
        return performance_metrics
    
    def calculate_quality_metrics(self, articles: List[Article], 
                                collection_timespan: timedelta) -> QualityMetrics:
        """品質メトリクスの計算"""
        try:
            # ソース多様性
            source_diversity = self._calculate_source_diversity(articles)
            
            # コンテンツ品質スコア
            content_quality = self._calculate_content_quality_score(articles)
            
            # 翻訳カバレッジ
            translation_coverage = self._calculate_translation_coverage(articles)
            
            # 緊急性検出率
            urgency_detection = self._calculate_urgency_detection_rate(articles)
            
            # カテゴリ分散バランス
            category_balance = self._calculate_category_distribution_balance(articles)
            
            # 時間的カバレッジ
            temporal_coverage = self._calculate_temporal_coverage(articles, collection_timespan)
            
            return QualityMetrics(
                source_diversity=source_diversity,
                content_quality_score=content_quality,
                translation_coverage=translation_coverage,
                urgency_detection_rate=urgency_detection,
                category_distribution_balance=category_balance,
                temporal_coverage=temporal_coverage
            )
            
        except Exception as e:
            self.logger.error(f"Failed to calculate quality metrics: {e}")
            return QualityMetrics(
                source_diversity=0.0,
                content_quality_score=0.0,
                translation_coverage=0.0,
                urgency_detection_rate=0.0,
                category_distribution_balance=0.0,
                temporal_coverage=0.0
            )
    
    def generate_analytics_report(self, time_range: timedelta = None) -> Dict[str, Any]:
        """分析レポート生成"""
        if time_range is None:
            time_range = timedelta(days=7)  # デフォルト7日間
        
        end_time = datetime.now()
        start_time = end_time - time_range
        
        try:
            # 期間内のメトリクスを取得
            historical_metrics = self._get_historical_metrics(start_time, end_time)
            
            if not historical_metrics:
                return {
                    'error': 'No metrics data available for the specified time range',
                    'time_range': f"{start_time.isoformat()} to {end_time.isoformat()}"
                }
            
            # トレンド分析
            trends = self._analyze_trends(historical_metrics)
            
            # 異常検出
            anomalies = self._detect_anomalies(historical_metrics)
            
            # パフォーマンス サマリー
            performance_summary = self._generate_performance_summary(historical_metrics)
            
            # 推奨事項
            recommendations = self._generate_recommendations(historical_metrics, trends, anomalies)
            
            report = {
                'report_metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'time_range': {
                        'start': start_time.isoformat(),
                        'end': end_time.isoformat(),
                        'duration_days': time_range.days
                    },
                    'metrics_count': len(historical_metrics)
                },
                'performance_summary': performance_summary,
                'trends': trends,
                'anomalies': anomalies,
                'recommendations': recommendations,
                'data_quality_assessment': self._assess_data_quality(historical_metrics)
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate analytics report: {e}")
            return {
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }
    
    def _calculate_basic_statistics(self, articles: List[Article]) -> Dict[str, Any]:
        """基本統計の計算"""
        if not articles:
            return {
                'by_source': {},
                'by_category': {},
                'by_language': {},
                'avg_importance': 0.0,
                'urgent_count': 0
            }
        
        # ソース別統計
        by_source = Counter(str(article.source) for article in articles)
        
        # カテゴリ別統計
        by_category = Counter(
            article.category.value if hasattr(article.category, 'value') else str(article.category) 
            for article in articles
        )
        
        # 言語別統計
        by_language = Counter(
            article.language.value if hasattr(article.language, 'value') else str(article.language) 
            for article in articles
        )
        
        # 重要度平均
        importance_scores = [
            article.importance_score for article in articles 
            if hasattr(article, 'importance_score') and article.importance_score is not None
        ]
        avg_importance = statistics.mean(importance_scores) if importance_scores else 0.0
        
        # 緊急記事数
        urgent_count = sum(
            1 for article in articles 
            if hasattr(article, 'is_urgent') and article.is_urgent
        )
        
        return {
            'by_source': dict(by_source),
            'by_category': dict(by_category),
            'by_language': dict(by_language),
            'avg_importance': avg_importance,
            'urgent_count': urgent_count
        }
    
    def _calculate_performance_statistics(self, collection_results: List[Any]) -> Dict[str, Any]:
        """パフォーマンス統計の計算"""
        if not collection_results:
            return {'success_rate': 0.0}
        
        successful_results = sum(1 for r in collection_results if hasattr(r, 'success') and r.success)
        success_rate = (successful_results / len(collection_results)) * 100
        
        return {
            'success_rate': success_rate,
            'total_results': len(collection_results),
            'successful_results': successful_results
        }
    
    def _calculate_cache_hit_rate(self, stats: Dict[str, Any]) -> float:
        """キャッシュヒット率計算"""
        cache_hits = stats.get('cache_hits', 0)
        cache_misses = stats.get('cache_misses', 0)
        total_requests = cache_hits + cache_misses
        
        return (cache_hits / total_requests * 100) if total_requests > 0 else 0.0
    
    def _calculate_error_rate(self, stats: Dict[str, Any]) -> float:
        """エラー率計算"""
        failed_requests = stats.get('failed_requests', 0)
        total_requests = stats.get('requests_made', 0)
        
        return (failed_requests / total_requests * 100) if total_requests > 0 else 0.0
    
    def _calculate_source_diversity(self, articles: List[Article]) -> float:
        """ソース多様性計算"""
        if not articles:
            return 0.0
        
        sources = set(str(article.source) for article in articles)
        unique_sources = len(sources)
        
        # シャノン多様性指数の簡易版
        source_counts = Counter(str(article.source) for article in articles)
        total_articles = len(articles)
        
        diversity_score = 0.0
        for count in source_counts.values():
            proportion = count / total_articles
            if proportion > 0:
                diversity_score -= proportion * (proportion ** 0.5)  # 簡易計算
        
        # 0-100スケールに正規化
        return min(diversity_score * 100, 100.0)
    
    def _calculate_content_quality_score(self, articles: List[Article]) -> float:
        """コンテンツ品質スコア計算"""
        if not articles:
            return 0.0
        
        quality_scores = []
        
        for article in articles:
            score = 0.0
            
            # タイトル品質
            title = article.title or ""
            if len(title) >= 20:
                score += 25
            elif len(title) >= 10:
                score += 15
            
            # コンテンツ品質
            content = article.content or ""
            if len(content) >= 500:
                score += 25
            elif len(content) >= 200:
                score += 15
            elif len(content) >= 50:
                score += 10
            
            # 翻訳品質
            if hasattr(article, 'title_translated') and article.title_translated:
                score += 20
            if hasattr(article, 'content_translated') and article.content_translated:
                score += 20
            
            # 分析品質
            if hasattr(article, 'summary') and article.summary:
                score += 10
            
            quality_scores.append(score)
        
        return statistics.mean(quality_scores) if quality_scores else 0.0
    
    def _calculate_translation_coverage(self, articles: List[Article]) -> float:
        """翻訳カバレッジ計算"""
        if not articles:
            return 0.0
        
        translated_count = sum(
            1 for article in articles 
            if (hasattr(article, 'title_translated') and article.title_translated) or
               (hasattr(article, 'content_translated') and article.content_translated)
        )
        
        return (translated_count / len(articles)) * 100
    
    def _calculate_urgency_detection_rate(self, articles: List[Article]) -> float:
        """緊急性検出率計算"""
        if not articles:
            return 0.0
        
        # 高重要度記事のうち緊急フラグが設定されている率
        high_importance_articles = [
            article for article in articles 
            if hasattr(article, 'importance_score') and article.importance_score and article.importance_score >= 8
        ]
        
        if not high_importance_articles:
            return 0.0
        
        urgent_detected = sum(
            1 for article in high_importance_articles 
            if hasattr(article, 'is_urgent') and article.is_urgent
        )
        
        return (urgent_detected / len(high_importance_articles)) * 100
    
    def _calculate_category_distribution_balance(self, articles: List[Article]) -> float:
        """カテゴリ分散バランス計算"""
        if not articles:
            return 0.0
        
        category_counts = Counter(
            article.category.value if hasattr(article.category, 'value') else str(article.category) 
            for article in articles
        )
        
        if len(category_counts) <= 1:
            return 0.0
        
        # 理想的な均等分散からの偏差を計算
        expected_per_category = len(articles) / len(category_counts)
        variance = statistics.variance(category_counts.values())
        
        # 低い分散ほど高いバランススコア
        balance_score = max(0, 100 - (variance / expected_per_category) * 10)
        
        return min(balance_score, 100.0)
    
    def _calculate_temporal_coverage(self, articles: List[Article], timespan: timedelta) -> float:
        """時間的カバレッジ計算"""
        if not articles:
            return 0.0
        
        # 公開日時が設定されている記事の時間分布
        dated_articles = [
            article for article in articles 
            if hasattr(article, 'published_at') and article.published_at
        ]
        
        if not dated_articles:
            return 0.0
        
        # 時間範囲を複数の区間に分割して分布を確認
        time_buckets = 12  # 12区間
        bucket_duration = timespan / time_buckets
        
        now = datetime.now()
        bucket_counts = [0] * time_buckets
        
        for article in dated_articles:
            try:
                if isinstance(article.published_at, str):
                    pub_time = datetime.fromisoformat(article.published_at.replace('Z', '+00:00'))
                else:
                    pub_time = article.published_at
                
                time_diff = now - pub_time
                if time_diff <= timespan:
                    bucket_index = int(time_diff / bucket_duration)
                    if 0 <= bucket_index < time_buckets:
                        bucket_counts[bucket_index] += 1
                        
            except (ValueError, TypeError, AttributeError):
                continue
        
        # 各区間に記事があるかをチェック
        covered_buckets = sum(1 for count in bucket_counts if count > 0)
        
        return (covered_buckets / time_buckets) * 100
    
    def _store_metrics(self, metrics: CollectionMetrics):
        """メトリクスをキャッシュに保存"""
        try:
            # 日別サマリー用のキー
            date_key = datetime.fromisoformat(metrics.timestamp).strftime('%Y-%m-%d')
            daily_key = f"analytics:daily:{date_key}"
            
            # 時間別詳細データ用のキー
            hour_key = datetime.fromisoformat(metrics.timestamp).strftime('%Y-%m-%d:%H')
            hourly_key = f"analytics:hourly:{hour_key}"
            
            # メトリクスをJSON化
            metrics_data = asdict(metrics)
            
            # 保存
            self.cache.set(
                daily_key, 
                json.dumps(metrics_data), 
                expire=86400 * self.metrics_retention_days,
                category='analytics'
            )
            
            self.cache.set(
                hourly_key, 
                json.dumps(metrics_data), 
                expire=3600 * self.detailed_metrics_retention_hours,
                category='analytics'
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store metrics: {e}")
    
    def _get_historical_metrics(self, start_time: datetime, end_time: datetime) -> List[CollectionMetrics]:
        """期間内の履歴メトリクスを取得"""
        metrics = []
        
        try:
            current_time = start_time
            while current_time <= end_time:
                date_key = current_time.strftime('%Y-%m-%d')
                daily_key = f"analytics:daily:{date_key}"
                
                cached_data = self.cache.get(daily_key, category='analytics')
                if cached_data:
                    try:
                        metrics_data = json.loads(cached_data)
                        metrics.append(CollectionMetrics(**metrics_data))
                    except (json.JSONDecodeError, TypeError) as e:
                        self.logger.warning(f"Failed to parse cached metrics for {date_key}: {e}")
                
                current_time += timedelta(days=1)
                
        except Exception as e:
            self.logger.error(f"Failed to get historical metrics: {e}")
        
        return metrics
    
    def _analyze_trends(self, metrics: List[CollectionMetrics]) -> Dict[str, Any]:
        """トレンド分析"""
        if len(metrics) < 2:
            return {'error': 'Insufficient data for trend analysis'}
        
        try:
            # 記事数のトレンド
            article_counts = [m.total_articles for m in metrics]
            article_trend = self._calculate_trend(article_counts)
            
            # 成功率のトレンド
            success_rates = [m.success_rate for m in metrics]
            success_trend = self._calculate_trend(success_rates)
            
            # 処理時間のトレンド
            processing_times = [m.processing_time for m in metrics]
            processing_trend = self._calculate_trend(processing_times)
            
            # 重要度のトレンド
            importance_scores = [m.average_importance for m in metrics]
            importance_trend = self._calculate_trend(importance_scores)
            
            return {
                'article_count_trend': article_trend,
                'success_rate_trend': success_trend,
                'processing_time_trend': processing_trend,
                'importance_score_trend': importance_trend,
                'analysis_period': f"{len(metrics)} data points"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze trends: {e}")
            return {'error': str(e)}
    
    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """トレンド計算"""
        if len(values) < 2:
            return {'direction': 'insufficient_data', 'change': 0.0}
        
        # 簡単な線形トレンド計算
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        change_percent = ((second_avg - first_avg) / first_avg * 100) if first_avg != 0 else 0
        
        if abs(change_percent) < 5:
            direction = 'stable'
        elif change_percent > 0:
            direction = 'increasing'
        else:
            direction = 'decreasing'
        
        return {
            'direction': direction,
            'change_percent': round(change_percent, 2),
            'first_period_avg': round(first_avg, 2),
            'second_period_avg': round(second_avg, 2)
        }
    
    def _detect_anomalies(self, metrics: List[CollectionMetrics]) -> List[Dict[str, Any]]:
        """異常検出"""
        anomalies = []
        
        if len(metrics) < 3:
            return anomalies
        
        try:
            # 記事数の異常
            article_counts = [m.total_articles for m in metrics]
            article_anomalies = self._detect_statistical_anomalies(
                article_counts, 'article_count', [m.timestamp for m in metrics]
            )
            anomalies.extend(article_anomalies)
            
            # 成功率の異常
            success_rates = [m.success_rate for m in metrics]
            success_anomalies = self._detect_statistical_anomalies(
                success_rates, 'success_rate', [m.timestamp for m in metrics]
            )
            anomalies.extend(success_anomalies)
            
            # 処理時間の異常
            processing_times = [m.processing_time for m in metrics]
            processing_anomalies = self._detect_statistical_anomalies(
                processing_times, 'processing_time', [m.timestamp for m in metrics]
            )
            anomalies.extend(processing_anomalies)
            
        except Exception as e:
            self.logger.error(f"Failed to detect anomalies: {e}")
        
        return anomalies
    
    def _detect_statistical_anomalies(self, values: List[float], metric_name: str, 
                                    timestamps: List[str]) -> List[Dict[str, Any]]:
        """統計的異常検出"""
        anomalies = []
        
        if len(values) < 3:
            return anomalies
        
        try:
            mean_val = statistics.mean(values)
            stdev_val = statistics.stdev(values) if len(values) > 1 else 0
            
            # 2σ以上離れている値を異常とする
            threshold = 2 * stdev_val
            
            for i, (value, timestamp) in enumerate(zip(values, timestamps)):
                if abs(value - mean_val) > threshold:
                    anomalies.append({
                        'metric': metric_name,
                        'timestamp': timestamp,
                        'value': value,
                        'expected_range': [mean_val - threshold, mean_val + threshold],
                        'severity': 'high' if abs(value - mean_val) > 3 * stdev_val else 'medium'
                    })
                    
        except Exception as e:
            self.logger.warning(f"Failed to detect anomalies for {metric_name}: {e}")
        
        return anomalies
    
    def _generate_performance_summary(self, metrics: List[CollectionMetrics]) -> Dict[str, Any]:
        """パフォーマンスサマリー生成"""
        if not metrics:
            return {}
        
        try:
            # 各指標の統計
            article_counts = [m.total_articles for m in metrics]
            success_rates = [m.success_rate for m in metrics]
            processing_times = [m.processing_time for m in metrics]
            duplicate_rates = [m.duplicate_rate for m in metrics]
            
            return {
                'total_sessions': len(metrics),
                'article_collection': {
                    'total_articles': sum(article_counts),
                    'average_per_session': statistics.mean(article_counts),
                    'min_per_session': min(article_counts),
                    'max_per_session': max(article_counts)
                },
                'performance': {
                    'average_success_rate': statistics.mean(success_rates),
                    'average_processing_time': statistics.mean(processing_times),
                    'fastest_collection': min(processing_times),
                    'slowest_collection': max(processing_times)
                },
                'quality': {
                    'average_duplicate_rate': statistics.mean(duplicate_rates),
                    'best_duplicate_rate': min(duplicate_rates),
                    'worst_duplicate_rate': max(duplicate_rates)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate performance summary: {e}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, metrics: List[CollectionMetrics], 
                                trends: Dict[str, Any], 
                                anomalies: List[Dict[str, Any]]) -> List[str]:
        """推奨事項生成"""
        recommendations = []
        
        try:
            if not metrics:
                return ['No data available for recommendations']
            
            # 成功率のチェック
            avg_success_rate = statistics.mean([m.success_rate for m in metrics])
            if avg_success_rate < self.quality_thresholds['min_success_rate']:
                recommendations.append(
                    f"Success rate ({avg_success_rate:.1f}%) is below threshold "
                    f"({self.quality_thresholds['min_success_rate']}%). "
                    f"Check API keys and network connectivity."
                )
            
            # 重複率のチェック
            avg_duplicate_rate = statistics.mean([m.duplicate_rate for m in metrics])
            if avg_duplicate_rate > self.quality_thresholds['max_duplicate_rate']:
                recommendations.append(
                    f"Duplicate rate ({avg_duplicate_rate:.1f}%) is above threshold "
                    f"({self.quality_thresholds['max_duplicate_rate']}%). "
                    f"Consider improving deduplication algorithms."
                )
            
            # 処理時間のチェック
            avg_processing_time = statistics.mean([m.processing_time for m in metrics])
            if avg_processing_time > 120:  # 2分以上
                recommendations.append(
                    f"Average processing time ({avg_processing_time:.1f}s) is high. "
                    f"Consider optimizing collection processes or increasing concurrency."
                )
            
            # トレンドベースの推奨事項
            if trends.get('success_rate_trend', {}).get('direction') == 'decreasing':
                recommendations.append(
                    "Success rate is declining. Investigate potential API issues or service degradation."
                )
            
            if trends.get('processing_time_trend', {}).get('direction') == 'increasing':
                recommendations.append(
                    "Processing time is increasing. Consider performance optimization or scaling."
                )
            
            # 異常ベースの推奨事項
            high_severity_anomalies = [a for a in anomalies if a.get('severity') == 'high']
            if high_severity_anomalies:
                recommendations.append(
                    f"Detected {len(high_severity_anomalies)} high-severity anomalies. "
                    f"Investigate recent system changes or external factors."
                )
            
            # ソース多様性のチェック
            if metrics:
                recent_metrics = metrics[-1]
                source_count = len(recent_metrics.articles_by_source)
                if source_count < self.quality_thresholds['min_sources']:
                    recommendations.append(
                        f"Source diversity is low ({source_count} sources). "
                        f"Consider adding more news sources for better coverage."
                    )
            
            # デフォルト推奨事項
            if not recommendations:
                recommendations.append("Collection system is performing within normal parameters.")
            
        except Exception as e:
            self.logger.error(f"Failed to generate recommendations: {e}")
            recommendations.append(f"Error generating recommendations: {str(e)}")
        
        return recommendations
    
    def _assess_data_quality(self, metrics: List[CollectionMetrics]) -> Dict[str, Any]:
        """データ品質評価"""
        if not metrics:
            return {'overall_score': 0, 'assessment': 'No data available'}
        
        try:
            quality_score = 100.0
            issues = []
            
            # データ完全性チェック
            complete_sessions = sum(1 for m in metrics if m.total_articles > 0)
            completeness_rate = (complete_sessions / len(metrics)) * 100
            
            if completeness_rate < 90:
                quality_score -= 20
                issues.append(f"Low data completeness: {completeness_rate:.1f}%")
            
            # 成功率チェック
            avg_success_rate = statistics.mean([m.success_rate for m in metrics])
            if avg_success_rate < 80:
                quality_score -= 15
                issues.append(f"Low average success rate: {avg_success_rate:.1f}%")
            
            # 重複率チェック
            avg_duplicate_rate = statistics.mean([m.duplicate_rate for m in metrics])
            if avg_duplicate_rate > 30:
                quality_score -= 10
                issues.append(f"High duplicate rate: {avg_duplicate_rate:.1f}%")
            
            # 一貫性チェック
            processing_times = [m.processing_time for m in metrics]
            if len(processing_times) > 1:
                cv = statistics.stdev(processing_times) / statistics.mean(processing_times)
                if cv > 1.0:  # 変動係数が1以上
                    quality_score -= 10
                    issues.append("High variability in processing times")
            
            quality_score = max(quality_score, 0.0)
            
            return {
                'overall_score': quality_score,
                'grade': self._score_to_grade(quality_score),
                'completeness_rate': completeness_rate,
                'average_success_rate': avg_success_rate,
                'average_duplicate_rate': avg_duplicate_rate,
                'issues': issues
            }
            
        except Exception as e:
            self.logger.error(f"Failed to assess data quality: {e}")
            return {'overall_score': 0, 'assessment': f'Error: {str(e)}'}
    
    def _score_to_grade(self, score: float) -> str:
        """スコアをグレードに変換"""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
    
    def _check_alert_conditions(self, metrics: CollectionMetrics):
        """アラート条件チェック"""
        alerts = []
        
        try:
            # 成功率低下アラート
            if metrics.success_rate < 50:
                alerts.append({
                    'type': 'success_rate_critical',
                    'message': f"Critical: Success rate dropped to {metrics.success_rate:.1f}%",
                    'severity': 'critical'
                })
            elif metrics.success_rate < 80:
                alerts.append({
                    'type': 'success_rate_warning',
                    'message': f"Warning: Success rate is {metrics.success_rate:.1f}%",
                    'severity': 'warning'
                })
            
            # 記事数異常アラート
            if metrics.total_articles == 0:
                alerts.append({
                    'type': 'no_articles_collected',
                    'message': "Critical: No articles collected in this session",
                    'severity': 'critical'
                })
            elif metrics.total_articles < 10:
                alerts.append({
                    'type': 'low_article_count',
                    'message': f"Warning: Only {metrics.total_articles} articles collected",
                    'severity': 'warning'
                })
            
            # エラー多発アラート
            if len(metrics.errors) > 5:
                alerts.append({
                    'type': 'high_error_count',
                    'message': f"Warning: {len(metrics.errors)} errors in collection session",
                    'severity': 'warning'
                })
            
            # 処理時間アラート
            if metrics.processing_time > 300:  # 5分以上
                alerts.append({
                    'type': 'slow_processing',
                    'message': f"Warning: Processing took {metrics.processing_time:.1f}s",
                    'severity': 'warning'
                })
            
            # アラートがある場合はログ出力
            for alert in alerts:
                if alert['severity'] == 'critical':
                    self.logger.error(alert['message'])
                else:
                    self.logger.warning(alert['message'])
                    
        except Exception as e:
            self.logger.error(f"Failed to check alert conditions: {e}")
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """リアルタイムメトリクス取得"""
        try:
            # 最新の時間別データを取得
            current_hour = datetime.now().strftime('%Y-%m-%d:%H')
            hourly_key = f"analytics:hourly:{current_hour}"
            
            cached_data = self.cache.get(hourly_key, category='analytics')
            if cached_data:
                metrics_data = json.loads(cached_data)
                return {
                    'current_metrics': metrics_data,
                    'timestamp': metrics_data.get('timestamp'),
                    'status': 'available'
                }
            else:
                return {
                    'current_metrics': None,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'no_recent_data'
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get real-time metrics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }