"""
Emergency Alert System for Critical News Delivery
緊急アラートシステム - 重要度10・CVSS 9.0以上の即座配信 - CLAUDE.md仕様準拠
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import hashlib

from utils.config import get_config
from utils.logger import setup_logger
from utils.error_notifier import get_error_notifier
from models.enhanced_article import Article, ArticleCategory
from .email_delivery import GmailDeliveryService
from .report_generator import ReportGenerator
from utils.cache_manager import get_cache_manager


logger = logging.getLogger(__name__)


class AlertPriority(Enum):
    """Alert priority levels"""
    CRITICAL = "critical"      # CVSS >= 9.0 or importance >= 10
    HIGH = "high"             # CVSS >= 8.0 or importance >= 9
    MEDIUM = "medium"         # CVSS >= 7.0 or importance >= 8
    LOW = "low"               # Other alerts


@dataclass
class EmergencyAlert:
    """Emergency alert data structure"""
    alert_id: str
    priority: AlertPriority
    articles: List[Article]
    triggered_at: datetime
    criteria_met: List[str]
    is_security_related: bool
    alert_summary: str
    estimated_impact: str
    recommended_actions: List[str]
    
    @property
    def max_cvss_score(self) -> float:
        """Get maximum CVSS score from articles"""
        cvss_scores = [a.cvss_score for a in self.articles if a.cvss_score is not None]
        return max(cvss_scores) if cvss_scores else 0.0
    
    @property
    def max_importance_score(self) -> int:
        """Get maximum importance score from articles"""
        return max(a.importance_score for a in self.articles)
    
    @property
    def should_send_immediate(self) -> bool:
        """Check if alert should be sent immediately"""
        return (
            self.priority == AlertPriority.CRITICAL or
            self.max_cvss_score >= 9.0 or
            self.max_importance_score >= 10
        )


class EmergencyAlertSystem:
    """Emergency alert system for critical news delivery - CLAUDE.md specification compliant"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = setup_logger(__name__)
        self.cache = get_cache_manager()
        self.error_notifier = get_error_notifier()
        
        # Initialize services
        self.email_service = GmailDeliveryService(self.config)
        self.report_generator = ReportGenerator(self.config)
        
        # Alert configuration - CLAUDE.md compliant thresholds
        self.alert_thresholds = {
            'cvss_critical': 9.0,      # CLAUDE.md: CVSS 9.0以上は緊急
            'cvss_high': 8.0,
            'cvss_medium': 7.0,
            'importance_critical': 10,  # CLAUDE.md: 重要度10は緊急
            'importance_high': 9,
            'importance_medium': 8
        }
        
        # Alert cooldown to prevent spam
        self.alert_cooldown = {
            AlertPriority.CRITICAL: 300,   # 5 minutes
            AlertPriority.HIGH: 900,       # 15 minutes
            AlertPriority.MEDIUM: 1800,    # 30 minutes
            AlertPriority.LOW: 3600        # 1 hour
        }
        
        # Tracking sent alerts
        self.sent_alerts: Set[str] = set()
        self.last_alert_times: Dict[str, datetime] = {}
        
        # Load existing alert state
        self._load_alert_state()
    
    def _load_alert_state(self):
        """Load previously sent alerts state"""
        try:
            state_file = Path('emergency_alert_state.json')
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                
                self.sent_alerts = set(state.get('sent_alerts', []))
                
                # Parse last alert times
                last_times = state.get('last_alert_times', {})
                for key, time_str in last_times.items():
                    try:
                        self.last_alert_times[key] = datetime.fromisoformat(time_str)
                    except ValueError:
                        continue
                
                self.logger.info(f"Loaded alert state: {len(self.sent_alerts)} sent alerts")
        except Exception as e:
            self.logger.error(f"Failed to load alert state: {e}")
    
    def _save_alert_state(self):
        """Save current alert state"""
        try:
            state = {
                'sent_alerts': list(self.sent_alerts),
                'last_alert_times': {
                    key: time.isoformat() 
                    for key, time in self.last_alert_times.items()
                }
            }
            
            with open('emergency_alert_state.json', 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save alert state: {e}")
    
    async def check_and_send_alerts(self, articles: List[Article]) -> List[EmergencyAlert]:
        """Check articles and send emergency alerts if needed"""
        try:
            # Filter articles that meet emergency criteria
            emergency_articles = self._filter_emergency_articles(articles)
            
            if not emergency_articles:
                self.logger.debug("No emergency articles found")
                return []
            
            # Group articles into alerts
            alerts = await self._create_emergency_alerts(emergency_articles)
            
            # Send alerts
            sent_alerts = []
            for alert in alerts:
                if await self._should_send_alert(alert):
                    success = await self._send_emergency_alert(alert)
                    if success:
                        sent_alerts.append(alert)
                        self._mark_alert_sent(alert)
                    
            if sent_alerts:
                self._save_alert_state()
                self.logger.info(f"Sent {len(sent_alerts)} emergency alerts")
            
            return sent_alerts
            
        except Exception as e:
            self.logger.error(f"Emergency alert checking failed: {e}")
            await self.error_notifier.handle_error(e, "EmergencyAlertSystem.check_and_send_alerts")
            return []
    
    def _filter_emergency_articles(self, articles: List[Article]) -> List[Article]:
        """Filter articles that meet emergency alert criteria - CLAUDE.md compliant"""
        emergency_articles = []
        
        for article in articles:
            meets_criteria = False
            
            # CLAUDE.md criteria: CVSS 9.0以上
            if hasattr(article, 'cvss_score') and article.cvss_score is not None:
                if article.cvss_score >= self.alert_thresholds['cvss_critical']:
                    meets_criteria = True
            
            # CLAUDE.md criteria: 重要度10
            if article.importance_score >= self.alert_thresholds['importance_critical']:
                meets_criteria = True
            
            # High priority security articles
            if (article.category == ArticleCategory.SECURITY and 
                article.importance_score >= self.alert_thresholds['importance_high']):
                meets_criteria = True
            
            # Urgent flag
            if hasattr(article, 'is_urgent') and article.is_urgent:
                meets_criteria = True
            
            if meets_criteria:
                emergency_articles.append(article)
        
        self.logger.info(f"Found {len(emergency_articles)} emergency articles from {len(articles)} total")
        return emergency_articles
    
    async def _create_emergency_alerts(self, articles: List[Article]) -> List[EmergencyAlert]:
        """Create emergency alert objects from articles"""
        alerts = []
        
        try:
            # Group articles by priority and type
            grouped_articles = self._group_articles_for_alerts(articles)
            
            for group_key, group_articles in grouped_articles.items():
                alert = await self._create_single_alert(group_key, group_articles)
                if alert:
                    alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Failed to create emergency alerts: {e}")
            return []
    
    def _group_articles_for_alerts(self, articles: List[Article]) -> Dict[str, List[Article]]:
        """Group articles for alert generation"""
        groups = {}
        
        for article in articles:
            # Determine priority
            priority = self._determine_article_priority(article)
            
            # Determine grouping key
            if article.category == ArticleCategory.SECURITY:
                if hasattr(article, 'cvss_score') and article.cvss_score is not None:
                    group_key = f"security_cvss_{priority.value}"
                else:
                    group_key = f"security_general_{priority.value}"
            else:
                group_key = f"{article.category.value}_{priority.value}"
            
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(article)
        
        return groups
    
    def _determine_article_priority(self, article: Article) -> AlertPriority:
        """Determine alert priority for article"""
        # CVSS-based priority
        if hasattr(article, 'cvss_score') and article.cvss_score is not None:
            if article.cvss_score >= self.alert_thresholds['cvss_critical']:
                return AlertPriority.CRITICAL
            elif article.cvss_score >= self.alert_thresholds['cvss_high']:
                return AlertPriority.HIGH
            elif article.cvss_score >= self.alert_thresholds['cvss_medium']:
                return AlertPriority.MEDIUM
        
        # Importance-based priority
        if article.importance_score >= self.alert_thresholds['importance_critical']:
            return AlertPriority.CRITICAL
        elif article.importance_score >= self.alert_thresholds['importance_high']:
            return AlertPriority.HIGH
        elif article.importance_score >= self.alert_thresholds['importance_medium']:
            return AlertPriority.MEDIUM
        
        return AlertPriority.LOW
    
    async def _create_single_alert(self, group_key: str, articles: List[Article]) -> Optional[EmergencyAlert]:
        """Create single emergency alert from grouped articles"""
        try:
            if not articles:
                return None
            
            # Generate alert ID
            alert_id = self._generate_alert_id(articles)
            
            # Determine priority
            priority = max(self._determine_article_priority(a) for a in articles)
            
            # Analyze criteria met
            criteria_met = self._analyze_criteria_met(articles)
            
            # Check if security-related
            is_security_related = any(
                a.category == ArticleCategory.SECURITY or 
                (hasattr(a, 'cvss_score') and a.cvss_score is not None)
                for a in articles
            )
            
            # Generate summary and impact assessment
            alert_summary = await self._generate_alert_summary(articles)
            estimated_impact = self._assess_impact(articles)
            recommended_actions = self._generate_recommendations(articles)
            
            return EmergencyAlert(
                alert_id=alert_id,
                priority=priority,
                articles=articles,
                triggered_at=datetime.now(),
                criteria_met=criteria_met,
                is_security_related=is_security_related,
                alert_summary=alert_summary,
                estimated_impact=estimated_impact,
                recommended_actions=recommended_actions
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create single alert: {e}")
            return None
    
    def _generate_alert_id(self, articles: List[Article]) -> str:
        """Generate unique alert ID based on article content"""
        content_hash = hashlib.md5()
        
        for article in sorted(articles, key=lambda x: x.url):
            content_str = f"{article.url}|{article.importance_score}|{getattr(article, 'cvss_score', 0)}"
            content_hash.update(content_str.encode('utf-8'))
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        return f"ALERT_{timestamp}_{content_hash.hexdigest()[:8]}"
    
    def _analyze_criteria_met(self, articles: List[Article]) -> List[str]:
        """Analyze which criteria triggered the alert"""
        criteria = []
        
        max_importance = max(a.importance_score for a in articles)
        if max_importance >= self.alert_thresholds['importance_critical']:
            criteria.append(f"重要度スコア {max_importance} (閾値: {self.alert_thresholds['importance_critical']})")
        
        cvss_scores = [a.cvss_score for a in articles if a.cvss_score is not None]
        if cvss_scores:
            max_cvss = max(cvss_scores)
            if max_cvss >= self.alert_thresholds['cvss_critical']:
                criteria.append(f"CVSS スコア {max_cvss} (閾値: {self.alert_thresholds['cvss_critical']})")
        
        security_count = len([a for a in articles if a.category == ArticleCategory.SECURITY])
        if security_count > 0:
            criteria.append(f"セキュリティ関連記事 {security_count}件")
        
        urgent_count = len([a for a in articles if getattr(a, 'is_urgent', False)])
        if urgent_count > 0:
            criteria.append(f"緊急フラグ付き記事 {urgent_count}件")
        
        return criteria
    
    async def _generate_alert_summary(self, articles: List[Article]) -> str:
        """Generate alert summary using AI if available"""
        try:
            # Simple summary if AI not available
            article_count = len(articles)
            categories = set(a.category.display_name for a in articles)
            max_importance = max(a.importance_score for a in articles)
            
            cvss_scores = [a.cvss_score for a in articles if a.cvss_score is not None]
            max_cvss = max(cvss_scores) if cvss_scores else None
            
            summary = f"{article_count}件の緊急ニュースを検出。"
            summary += f"最高重要度: {max_importance}、"
            
            if max_cvss:
                summary += f"最高CVSS: {max_cvss}、"
            
            summary += f"対象カテゴリ: {', '.join(categories)}"
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to generate alert summary: {e}")
            return f"{len(articles)}件の緊急ニュースが検出されました。"
    
    def _assess_impact(self, articles: List[Article]) -> str:
        """Assess potential impact of the alert"""
        max_importance = max(a.importance_score for a in articles)
        cvss_scores = [a.cvss_score for a in articles if a.cvss_score is not None]
        max_cvss = max(cvss_scores) if cvss_scores else None
        
        if max_cvss and max_cvss >= 9.0:
            return "非常に高い - 即座の対応が必要"
        elif max_importance >= 10:
            return "高い - 緊急対応を推奨"
        elif max_cvss and max_cvss >= 8.0:
            return "中程度 - 迅速な確認が必要"
        elif max_importance >= 9:
            return "中程度 - 注意深い監視が必要"
        else:
            return "軽度 - 定期的な確認で十分"
    
    def _generate_recommendations(self, articles: List[Article]) -> List[str]:
        """Generate recommended actions based on articles"""
        recommendations = []
        
        # Security-specific recommendations
        security_articles = [a for a in articles if a.category == ArticleCategory.SECURITY]
        if security_articles:
            recommendations.extend([
                "システムセキュリティ状況の緊急確認",
                "影響を受ける可能性のあるシステムの特定",
                "緊急パッチの適用可能性の評価",
                "一時的な緩和策の実施検討"
            ])
        
        # High importance recommendations
        max_importance = max(a.importance_score for a in articles)
        if max_importance >= 10:
            recommendations.extend([
                "関係者への即座の情報共有",
                "緊急対応チームの招集検討",
                "メディア・広報対応の準備"
            ])
        
        # CVSS-based recommendations
        cvss_scores = [a.cvss_score for a in articles if a.cvss_score is not None]
        if cvss_scores and max(cvss_scores) >= 9.0:
            recommendations.extend([
                "インシデント対応手順の活性化",
                "システム監視レベルの強化",
                "バックアップ・復旧計画の確認"
            ])
        
        # General recommendations
        recommendations.extend([
            "詳細情報の継続的な監視",
            "対応記録の文書化",
            "関連システムへの影響評価"
        ])
        
        return recommendations[:7]  # Limit to 7 recommendations
    
    async def _should_send_alert(self, alert: EmergencyAlert) -> bool:
        """Determine if alert should be sent (cooldown check)"""
        # Check if already sent
        if alert.alert_id in self.sent_alerts:
            self.logger.debug(f"Alert {alert.alert_id} already sent")
            return False
        
        # Check cooldown for similar alerts
        cooldown_key = f"{alert.priority.value}_alert"
        if cooldown_key in self.last_alert_times:
            time_since_last = datetime.now() - self.last_alert_times[cooldown_key]
            cooldown_period = self.alert_cooldown[alert.priority]
            
            if time_since_last.total_seconds() < cooldown_period:
                self.logger.info(f"Alert cooldown active for {alert.priority.value}: {cooldown_period - time_since_last.total_seconds():.0f}s remaining")
                return False
        
        # Critical alerts always sent (override cooldown for CRITICAL)
        if alert.priority == AlertPriority.CRITICAL:
            return True
        
        return True
    
    async def _send_emergency_alert(self, alert: EmergencyAlert) -> bool:
        """Send emergency alert via email"""
        try:
            self.logger.info(f"Sending emergency alert: {alert.alert_id} ({alert.priority.value})")
            
            # Generate alert report
            report_files = await self._generate_alert_report(alert)
            
            # Send via email service
            if alert.is_security_related and alert.priority == AlertPriority.CRITICAL:
                # Use dedicated security alert method
                delivery_record = await self.email_service.send_urgent_security_alert(
                    [a.to_dict() for a in alert.articles],
                    len(alert.articles)
                )
            else:
                # Use general urgent alert method
                delivery_record = await self.email_service.send_urgent_alert(
                    report_files,
                    len(alert.articles)
                )
            
            success = delivery_record.status == 'success'
            
            if success:
                self.logger.info(f"Emergency alert {alert.alert_id} sent successfully")
            else:
                self.logger.error(f"Emergency alert {alert.alert_id} failed: {delivery_record.error_message}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send emergency alert {alert.alert_id}: {e}")
            await self.error_notifier.handle_error(e, f"EmergencyAlertSystem._send_emergency_alert({alert.alert_id})")
            return False
    
    async def _generate_alert_report(self, alert: EmergencyAlert) -> Dict[str, str]:
        """Generate report files for emergency alert"""
        try:
            # Generate reports using report generator
            report_files = await self.report_generator.generate_urgent_alert(alert.articles)
            
            return report_files
            
        except Exception as e:
            self.logger.error(f"Failed to generate alert report: {e}")
            return {}
    
    def _mark_alert_sent(self, alert: EmergencyAlert):
        """Mark alert as sent and update timing"""
        self.sent_alerts.add(alert.alert_id)
        cooldown_key = f"{alert.priority.value}_alert"
        self.last_alert_times[cooldown_key] = alert.triggered_at
        
        self.logger.debug(f"Marked alert {alert.alert_id} as sent")
    
    def get_alert_statistics(self, days_back: int = 7) -> Dict[str, Any]:
        """Get alert statistics for the past period"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days_back)
            
            # This would typically query a database
            # For now, return basic stats from current session
            stats = {
                'period_days': days_back,
                'total_alerts_sent': len(self.sent_alerts),
                'alert_types': {
                    'critical': 0,
                    'high': 0,
                    'medium': 0,
                    'low': 0
                },
                'security_alerts': 0,
                'last_alert_time': None,
                'alert_frequency': 0.0
            }
            
            # Calculate frequency if we have timing data
            if self.last_alert_times:
                latest_time = max(self.last_alert_times.values())
                if latest_time > cutoff_time:
                    stats['last_alert_time'] = latest_time.isoformat()
                    stats['alert_frequency'] = len(self.sent_alerts) / days_back
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get alert statistics: {e}")
            return {}
    
    def cleanup_old_alerts(self, days_to_keep: int = 30):
        """Clean up old alert state data"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days_to_keep)
            
            # Clean up old timing data
            old_keys = [
                key for key, time in self.last_alert_times.items()
                if time < cutoff_time
            ]
            
            for key in old_keys:
                del self.last_alert_times[key]
            
            # Note: sent_alerts set is kept to prevent re-sending
            # but could be cleaned up if we implement database storage
            
            self._save_alert_state()
            self.logger.info(f"Cleaned up {len(old_keys)} old alert timing entries")
            
        except Exception as e:
            self.logger.error(f"Alert cleanup failed: {e}")
    
    async def test_emergency_alert(self) -> bool:
        """Send test emergency alert"""
        try:
            # Create test article
            test_article = Article(
                url="https://test.example.com/emergency-test",
                title="テスト緊急アラート - システム動作確認",
                source_name="Emergency Alert Test System",
                category=ArticleCategory.SECURITY,
                published_at=datetime.now(),
                description="これは緊急アラートシステムのテスト配信です。",
                importance_score=10,
                cvss_score=9.5,
                is_urgent=True
            )
            
            # Create test alert
            test_alert = EmergencyAlert(
                alert_id=f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                priority=AlertPriority.CRITICAL,
                articles=[test_article],
                triggered_at=datetime.now(),
                criteria_met=["テスト実行", "システム動作確認"],
                is_security_related=True,
                alert_summary="緊急アラートシステムのテスト配信",
                estimated_impact="テスト - 実際の影響はありません",
                recommended_actions=["システム動作確認", "テスト完了の確認"]
            )
            
            # Send test alert
            success = await self._send_emergency_alert(test_alert)
            
            if success:
                self.logger.info("Test emergency alert sent successfully")
            else:
                self.logger.error("Test emergency alert failed")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Test emergency alert failed: {e}")
            return False
    
    def configure_alert_thresholds(self, new_thresholds: Dict[str, float]):
        """Configure alert thresholds"""
        try:
            for key, value in new_thresholds.items():
                if key in self.alert_thresholds:
                    self.alert_thresholds[key] = value
                    self.logger.info(f"Updated alert threshold {key}: {value}")
            
            # Save configuration
            config_file = Path('emergency_alert_config.json')
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.alert_thresholds, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            self.logger.error(f"Failed to configure alert thresholds: {e}")
    
    def get_alert_configuration(self) -> Dict[str, Any]:
        """Get current alert configuration"""
        return {
            'thresholds': self.alert_thresholds.copy(),
            'cooldown_periods': {
                priority.value: seconds 
                for priority, seconds in self.alert_cooldown.items()
            },
            'sent_alerts_count': len(self.sent_alerts),
            'last_cleanup': datetime.now().isoformat()
        }


# Global emergency alert system instance
_emergency_alert_system = None


def get_emergency_alert_system() -> EmergencyAlertSystem:
    """Get global emergency alert system instance"""
    global _emergency_alert_system
    if _emergency_alert_system is None:
        _emergency_alert_system = EmergencyAlertSystem()
    return _emergency_alert_system


async def check_emergency_alerts(articles: List[Article]) -> List[EmergencyAlert]:
    """Convenience function to check and send emergency alerts"""
    alert_system = get_emergency_alert_system()
    return await alert_system.check_and_send_alerts(articles)


# CLI interface for emergency alert management
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Emergency Alert System Management')
    parser.add_argument('--test', action='store_true', help='Send test emergency alert')
    parser.add_argument('--stats', action='store_true', help='Show alert statistics')
    parser.add_argument('--config', action='store_true', help='Show current configuration')
    parser.add_argument('--cleanup', type=int, help='Clean up alerts older than N days')
    parser.add_argument('--set-threshold', nargs=2, metavar=('KEY', 'VALUE'), 
                       help='Set alert threshold (e.g., cvss_critical 9.5)')
    
    args = parser.parse_args()
    
    async def main():
        alert_system = EmergencyAlertSystem()
        
        if args.test:
            print("Sending test emergency alert...")
            success = await alert_system.test_emergency_alert()
            print(f"Test result: {'SUCCESS' if success else 'FAILED'}")
        
        elif args.stats:
            print("Alert Statistics:")
            stats = alert_system.get_alert_statistics()
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        elif args.config:
            print("Alert Configuration:")
            config = alert_system.get_alert_configuration()
            print(json.dumps(config, indent=2, ensure_ascii=False))
        
        elif args.cleanup:
            print(f"Cleaning up alerts older than {args.cleanup} days...")
            alert_system.cleanup_old_alerts(args.cleanup)
            print("Cleanup completed")
        
        elif args.set_threshold:
            key, value = args.set_threshold
            try:
                alert_system.configure_alert_thresholds({key: float(value)})
                print(f"Updated threshold {key}: {value}")
            except ValueError:
                print("Error: Threshold value must be a number")
        
        else:
            parser.print_help()
    
    asyncio.run(main())