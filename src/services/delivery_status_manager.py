"""
Email Delivery Status Management System
メール配信状況管理システム
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from utils.config import get_config
from models.article import DeliveryRecord
from models.database import DatabaseManager


logger = logging.getLogger(__name__)


class DeliveryStatus(Enum):
    """配信ステータス"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    RETRYING = "retrying"


class DeliveryPriority(Enum):
    """配信優先度"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class DeliveryStatusRecord:
    """配信状況レコード"""
    delivery_id: str
    delivery_type: str
    status: DeliveryStatus
    priority: DeliveryPriority
    recipients: List[str]
    subject: str
    content_hash: str
    
    # タイムスタンプ
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 詳細情報
    article_count: int = 0
    urgent_count: int = 0
    report_format: str = ""
    report_paths: List[str] = None
    
    # エラー情報
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # 統計情報
    successful_sends: int = 0
    failed_sends: int = 0
    processing_time: float = 0.0
    
    def __post_init__(self):
        if self.report_paths is None:
            self.report_paths = []


class DeliveryStatusManager:
    """配信状況管理システム"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.db_manager = DatabaseManager(self.config)
        
        # 配信キュー
        self.pending_deliveries: Dict[str, DeliveryStatusRecord] = {}
        self.active_deliveries: Dict[str, DeliveryStatusRecord] = {}
        self.completed_deliveries: Dict[str, DeliveryStatusRecord] = {}
        
        # 設定
        self.max_concurrent_deliveries = self.config.get('delivery.max_concurrent', default=3)
        self.retry_delay_seconds = self.config.get('delivery.retry_delay', default=60)
        self.cleanup_age_days = self.config.get('delivery.cleanup_age_days', default=30)
        
        logger.info("Delivery Status Manager initialized")
    
    def create_delivery_record(self, delivery_type: str, recipients: List[str],
                             subject: str, content_hash: str,
                             priority: DeliveryPriority = DeliveryPriority.NORMAL,
                             article_count: int = 0, urgent_count: int = 0,
                             report_paths: List[str] = None) -> str:
        """新しい配信レコードを作成"""
        try:
            # Generate unique delivery ID
            delivery_id = f"{delivery_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(content_hash) % 10000:04d}"
            
            # Create delivery record
            delivery_record = DeliveryStatusRecord(
                delivery_id=delivery_id,
                delivery_type=delivery_type,
                status=DeliveryStatus.PENDING,
                priority=priority,
                recipients=recipients,
                subject=subject,
                content_hash=content_hash,
                created_at=datetime.now(),
                article_count=article_count,
                urgent_count=urgent_count,
                report_paths=report_paths or []
            )
            
            # Add to pending queue
            self.pending_deliveries[delivery_id] = delivery_record
            
            logger.info(f"Created delivery record: {delivery_id} ({delivery_type})")
            return delivery_id
            
        except Exception as e:
            logger.error(f"Failed to create delivery record: {e}")
            raise
    
    def update_delivery_status(self, delivery_id: str, status: DeliveryStatus,
                             error_message: str = None, 
                             successful_sends: int = None,
                             failed_sends: int = None,
                             processing_time: float = None):
        """配信状況を更新"""
        try:
            # Find delivery record
            delivery_record = self._find_delivery_record(delivery_id)
            if not delivery_record:
                logger.warning(f"Delivery record not found: {delivery_id}")
                return
            
            # Update status
            old_status = delivery_record.status
            delivery_record.status = status
            
            # Update timestamps
            now = datetime.now()
            if status == DeliveryStatus.IN_PROGRESS and not delivery_record.started_at:
                delivery_record.started_at = now
            elif status in [DeliveryStatus.SUCCESS, DeliveryStatus.FAILED, DeliveryStatus.PARTIAL]:
                delivery_record.completed_at = now
            
            # Update details
            if error_message:
                delivery_record.error_message = error_message
            if successful_sends is not None:
                delivery_record.successful_sends = successful_sends
            if failed_sends is not None:
                delivery_record.failed_sends = failed_sends
            if processing_time is not None:
                delivery_record.processing_time = processing_time
            
            # Move between queues if necessary
            self._move_delivery_record(delivery_id, old_status, status)
            
            # Save to database
            self._save_delivery_record(delivery_record)
            
            logger.info(f"Updated delivery {delivery_id}: {old_status.value} -> {status.value}")
            
        except Exception as e:
            logger.error(f"Failed to update delivery status: {e}")
    
    def _find_delivery_record(self, delivery_id: str) -> Optional[DeliveryStatusRecord]:
        """配信レコードを検索"""
        for queue in [self.pending_deliveries, self.active_deliveries, self.completed_deliveries]:
            if delivery_id in queue:
                return queue[delivery_id]
        return None
    
    def _move_delivery_record(self, delivery_id: str, old_status: DeliveryStatus, new_status: DeliveryStatus):
        """配信レコードをキュー間で移動"""
        delivery_record = None
        
        # Remove from current queue
        if old_status == DeliveryStatus.PENDING and delivery_id in self.pending_deliveries:
            delivery_record = self.pending_deliveries.pop(delivery_id)
        elif old_status in [DeliveryStatus.IN_PROGRESS, DeliveryStatus.RETRYING] and delivery_id in self.active_deliveries:
            delivery_record = self.active_deliveries.pop(delivery_id)
        elif old_status in [DeliveryStatus.SUCCESS, DeliveryStatus.FAILED, DeliveryStatus.PARTIAL] and delivery_id in self.completed_deliveries:
            delivery_record = self.completed_deliveries.pop(delivery_id)
        
        if not delivery_record:
            return
        
        # Add to new queue
        if new_status == DeliveryStatus.PENDING:
            self.pending_deliveries[delivery_id] = delivery_record
        elif new_status in [DeliveryStatus.IN_PROGRESS, DeliveryStatus.RETRYING]:
            self.active_deliveries[delivery_id] = delivery_record
        elif new_status in [DeliveryStatus.SUCCESS, DeliveryStatus.FAILED, DeliveryStatus.PARTIAL]:
            self.completed_deliveries[delivery_id] = delivery_record
    
    def get_next_pending_delivery(self) -> Optional[DeliveryStatusRecord]:
        """次の処理待ち配信を取得（優先度順）"""
        if not self.pending_deliveries:
            return None
        
        # Sort by priority and created time
        priority_order = {
            DeliveryPriority.URGENT: 0,
            DeliveryPriority.HIGH: 1,
            DeliveryPriority.NORMAL: 2,
            DeliveryPriority.LOW: 3
        }
        
        sorted_deliveries = sorted(
            self.pending_deliveries.values(),
            key=lambda x: (priority_order.get(x.priority, 999), x.created_at)
        )
        
        return sorted_deliveries[0] if sorted_deliveries else None
    
    def can_start_new_delivery(self) -> bool:
        """新しい配信を開始できるかチェック"""
        return len(self.active_deliveries) < self.max_concurrent_deliveries
    
    def mark_delivery_for_retry(self, delivery_id: str, error_message: str = None):
        """配信を再試行対象としてマーク"""
        try:
            delivery_record = self._find_delivery_record(delivery_id)
            if not delivery_record:
                logger.warning(f"Delivery record not found for retry: {delivery_id}")
                return
            
            # Check retry limit
            if delivery_record.retry_count >= delivery_record.max_retries:
                logger.warning(f"Max retries exceeded for delivery: {delivery_id}")
                self.update_delivery_status(delivery_id, DeliveryStatus.FAILED, error_message)
                return
            
            # Increment retry count
            delivery_record.retry_count += 1
            if error_message:
                delivery_record.error_message = error_message
            
            # Schedule retry after delay
            retry_time = datetime.now() + timedelta(seconds=self.retry_delay_seconds * delivery_record.retry_count)
            delivery_record.created_at = retry_time  # Use created_at as retry time
            
            # Move to pending for retry
            self.update_delivery_status(delivery_id, DeliveryStatus.PENDING)
            
            logger.info(f"Scheduled retry {delivery_record.retry_count}/{delivery_record.max_retries} for delivery: {delivery_id}")
            
        except Exception as e:
            logger.error(f"Failed to mark delivery for retry: {e}")
    
    def get_delivery_statistics(self) -> Dict[str, Any]:
        """配信統計情報を取得"""
        try:
            total_pending = len(self.pending_deliveries)
            total_active = len(self.active_deliveries)
            total_completed = len(self.completed_deliveries)
            
            # Recent success rate (last 24 hours)
            recent_cutoff = datetime.now() - timedelta(hours=24)
            recent_completed = [
                d for d in self.completed_deliveries.values()
                if d.completed_at and d.completed_at >= recent_cutoff
            ]
            
            recent_successful = len([d for d in recent_completed if d.status == DeliveryStatus.SUCCESS])
            recent_total = len(recent_completed)
            success_rate = (recent_successful / recent_total * 100) if recent_total > 0 else 0
            
            # Average processing time
            processing_times = [d.processing_time for d in recent_completed if d.processing_time > 0]
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            
            # Priority distribution
            priority_counts = {}
            for delivery in self.pending_deliveries.values():
                priority = delivery.priority.value
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            return {
                'total_pending': total_pending,
                'total_active': total_active,
                'total_completed': total_completed,
                'recent_success_rate': round(success_rate, 2),
                'avg_processing_time': round(avg_processing_time, 2),
                'priority_distribution': priority_counts,
                'max_concurrent': self.max_concurrent_deliveries,
                'can_start_new': self.can_start_new_delivery()
            }
            
        except Exception as e:
            logger.error(f"Failed to get delivery statistics: {e}")
            return {}
    
    def get_delivery_history(self, limit: int = 50, delivery_type: str = None) -> List[Dict[str, Any]]:
        """配信履歴を取得"""
        try:
            all_deliveries = []
            
            # Collect from all queues
            for queue in [self.completed_deliveries, self.active_deliveries, self.pending_deliveries]:
                all_deliveries.extend(queue.values())
            
            # Filter by type if specified
            if delivery_type:
                all_deliveries = [d for d in all_deliveries if d.delivery_type == delivery_type]
            
            # Sort by created time (newest first)
            all_deliveries.sort(key=lambda x: x.created_at, reverse=True)
            
            # Convert to dict and limit
            result = []
            for delivery in all_deliveries[:limit]:
                delivery_dict = asdict(delivery)
                # Convert datetime objects to strings
                for key, value in delivery_dict.items():
                    if isinstance(value, datetime):
                        delivery_dict[key] = value.isoformat() if value else None
                    elif isinstance(value, (DeliveryStatus, DeliveryPriority)):
                        delivery_dict[key] = value.value
                result.append(delivery_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get delivery history: {e}")
            return []
    
    def _save_delivery_record(self, delivery_record: DeliveryStatusRecord):
        """配信レコードをデータベースに保存"""
        try:
            # Convert to database record format
            db_record = {
                'delivery_id': delivery_record.delivery_id,
                'delivery_type': delivery_record.delivery_type,
                'recipients': json.dumps(delivery_record.recipients),
                'subject': delivery_record.subject,
                'status': delivery_record.status.value,
                'article_count': delivery_record.article_count,
                'urgent_count': delivery_record.urgent_count,
                'content_hash': delivery_record.content_hash,
                'error_message': delivery_record.error_message,
                'report_format': delivery_record.report_format,
                'report_path': ','.join(delivery_record.report_paths) if delivery_record.report_paths else None,
                'delivered_at': delivery_record.completed_at or delivery_record.started_at or delivery_record.created_at
            }
            
            # Save to database (using existing delivery_history table)
            # This would integrate with the DatabaseManager
            # For now, log the save operation
            logger.debug(f"Saving delivery record to database: {delivery_record.delivery_id}")
            
        except Exception as e:
            logger.error(f"Failed to save delivery record to database: {e}")
    
    def cleanup_old_records(self) -> int:
        """古い配信レコードをクリーンアップ"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.cleanup_age_days)
            cleaned_count = 0
            
            # Clean completed deliveries
            to_remove = []
            for delivery_id, delivery_record in self.completed_deliveries.items():
                if delivery_record.completed_at and delivery_record.completed_at < cutoff_date:
                    to_remove.append(delivery_id)
            
            for delivery_id in to_remove:
                del self.completed_deliveries[delivery_id]
                cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} old delivery records")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
            return 0
    
    def get_failed_deliveries(self) -> List[DeliveryStatusRecord]:
        """失敗した配信のリストを取得"""
        return [
            delivery for delivery in self.completed_deliveries.values()
            if delivery.status == DeliveryStatus.FAILED
        ]
    
    def get_delivery_details(self, delivery_id: str) -> Optional[Dict[str, Any]]:
        """特定の配信の詳細情報を取得"""
        delivery_record = self._find_delivery_record(delivery_id)
        if not delivery_record:
            return None
        
        delivery_dict = asdict(delivery_record)
        # Convert datetime and enum objects
        for key, value in delivery_dict.items():
            if isinstance(value, datetime):
                delivery_dict[key] = value.isoformat() if value else None
            elif isinstance(value, (DeliveryStatus, DeliveryPriority)):
                delivery_dict[key] = value.value
        
        return delivery_dict
    
    async def monitor_deliveries(self):
        """配信状況を定期的に監視"""
        try:
            while True:
                # Check for stuck deliveries
                stuck_threshold = datetime.now() - timedelta(minutes=30)
                
                for delivery_id, delivery_record in list(self.active_deliveries.items()):
                    if (delivery_record.started_at and 
                        delivery_record.started_at < stuck_threshold and
                        delivery_record.status == DeliveryStatus.IN_PROGRESS):
                        
                        logger.warning(f"Delivery appears stuck: {delivery_id}")
                        self.mark_delivery_for_retry(delivery_id, "Delivery timeout")
                
                # Cleanup old records periodically
                if datetime.now().minute == 0:  # Once per hour
                    self.cleanup_old_records()
                
                await asyncio.sleep(60)  # Check every minute
                
        except asyncio.CancelledError:
            logger.info("Delivery monitoring stopped")
        except Exception as e:
            logger.error(f"Delivery monitoring error: {e}")


# Global delivery status manager instance
_delivery_status_manager_instance = None


def get_delivery_status_manager() -> DeliveryStatusManager:
    """グローバル配信状況管理インスタンスの取得"""
    global _delivery_status_manager_instance
    if _delivery_status_manager_instance is None:
        _delivery_status_manager_instance = DeliveryStatusManager()
    return _delivery_status_manager_instance