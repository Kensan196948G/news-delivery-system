# NEWS-Scheduler - スケジューラー管理エージェント

## エージェント概要
ニュース配信システムのスケジューリング、タスク実行、時間ベースの自動処理を管理するエージェント。

## 役割と責任
- スケジュール管理・実行
- タスクスケジューラー制御
- 時間ベース処理制御
- バッチジョブ管理
- 緊急配信トリガー管理

## 主要業務

### スケジュール管理
```python
import schedule
import asyncio
from datetime import datetime, time
from typing import Dict, List, Callable

class NewsScheduler:
    def __init__(self):
        self.jobs = {}
        self.running = False
        self.emergency_triggers = []
        
    def setup_daily_schedule(self):
        """日次スケジュール設定"""
        # 定期配信スケジュール
        schedule.every().day.at("07:00").do(
            self._schedule_job,
            job_name="morning_delivery",
            job_func=self.trigger_news_collection_and_delivery
        )
        
        schedule.every().day.at("12:00").do(
            self._schedule_job,
            job_name="noon_delivery", 
            job_func=self.trigger_news_collection_and_delivery
        )
        
        schedule.every().day.at("18:00").do(
            self._schedule_job,
            job_name="evening_delivery",
            job_func=self.trigger_news_collection_and_delivery
        )
        
        # システムメンテナンススケジュール
        schedule.every().day.at("02:00").do(
            self._schedule_job,
            job_name="daily_maintenance",
            job_func=self.run_daily_maintenance
        )
        
        # 週次・月次処理
        schedule.every().sunday.at("01:00").do(
            self._schedule_job,
            job_name="weekly_report",
            job_func=self.generate_weekly_report
        )
        
    async def trigger_news_collection_and_delivery(self):
        """ニュース収集・配信の実行"""
        try:
            self.logger.info("Starting scheduled news collection and delivery")
            
            # 1. ニュース収集
            collection_result = await self.news_collector.collect_all_categories()
            
            # 2. 重複除去・処理
            processed_articles = await self.article_processor.process_articles(
                collection_result.articles
            )
            
            # 3. 翻訳処理
            translated_articles = await self.translator.translate_batch(processed_articles)
            
            # 4. AI分析
            analyzed_articles = await self.analyzer.analyze_batch(translated_articles)
            
            # 5. 緊急配信チェック
            urgent_articles = [a for a in analyzed_articles if a.importance_score >= 10]
            if urgent_articles:
                await self.trigger_emergency_delivery(urgent_articles)
            
            # 6. 通常配信
            await self.delivery_service.send_scheduled_delivery(analyzed_articles)
            
            self.logger.info(f"Scheduled delivery completed: {len(analyzed_articles)} articles")
            
        except Exception as e:
            self.logger.error(f"Scheduled job failed: {str(e)}")
            await self.notification_service.send_error_alert(e)
```

### 緊急配信トリガー
```python
class EmergencyTrigger:
    def __init__(self):
        self.trigger_conditions = {
            'high_importance': lambda article: article.importance_score >= 10,
            'security_critical': lambda article: hasattr(article, 'cvss_score') and article.cvss_score >= 9.0,
            'breaking_news': lambda article: 'breaking' in article.title.lower(),
            'system_alert': lambda article: article.category == 'system_alert'
        }
        
    async def check_emergency_conditions(self, article: Article) -> bool:
        """緊急配信条件チェック"""
        for condition_name, condition_func in self.trigger_conditions.items():
            if condition_func(article):
                self.logger.warning(
                    f"Emergency trigger activated: {condition_name} for article {article.id}"
                )
                return True
        return False
    
    async def trigger_emergency_delivery(self, articles: List[Article]):
        """緊急配信実行"""
        try:
            # 緊急レポート生成
            emergency_report = await self.report_generator.generate_emergency_report(articles)
            
            # 緊急配信
            await self.delivery_service.send_emergency_delivery(
                articles=articles,
                report=emergency_report,
                priority=True
            )
            
            # 緊急配信履歴記録
            await self.db.record_emergency_delivery(articles)
            
        except Exception as e:
            self.logger.error(f"Emergency delivery failed: {str(e)}")
```

### Windows タスクスケジューラー連携
```python
import subprocess
import xml.etree.ElementTree as ET

class WindowsTaskScheduler:
    def __init__(self):
        self.task_name = "NewsDeliverySystem"
        self.python_path = r"C:\Python311\python.exe"
        self.script_path = r"C:\NewsDeliverySystem\src\main.py"
        
    def create_scheduled_tasks(self):
        """Windows タスクスケジューラーにタスク登録"""
        triggers = [
            {"time": "07:00", "name": "MorningDelivery"},
            {"time": "12:00", "name": "NoonDelivery"}, 
            {"time": "18:00", "name": "EveningDelivery"}
        ]
        
        for trigger in triggers:
            task_xml = self._generate_task_xml(trigger)
            self._register_task(f"{self.task_name}_{trigger['name']}", task_xml)
    
    def _generate_task_xml(self, trigger: Dict) -> str:
        """タスク定義XML生成"""
        return f"""<?xml version="1.0" encoding="UTF-16"?>
        <Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
            <Triggers>
                <CalendarTrigger>
                    <StartBoundary>2024-01-01T{trigger['time']}:00</StartBoundary>
                    <ScheduleByDay>
                        <DaysInterval>1</DaysInterval>
                    </ScheduleByDay>
                </CalendarTrigger>
            </Triggers>
            <Actions>
                <Exec>
                    <Command>{self.python_path}</Command>
                    <Arguments>{self.script_path}</Arguments>
                    <WorkingDirectory>C:\\NewsDeliverySystem\\src</WorkingDirectory>
                </Exec>
            </Actions>
            <Settings>
                <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
                <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
                <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
                <AllowHardTerminate>true</AllowHardTerminate>
                <StartWhenAvailable>true</StartWhenAvailable>
                <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
                <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
            </Settings>
        </Task>"""
```

## 使用する技術・ツール
- **Python**: schedule, asyncio, datetime
- **Windows**: タスクスケジューラー, PowerShell
- **監視**: logging, prometheus_client
- **通知**: smtplib, slack-sdk
- **設定**: configparser, yaml
- **データベース**: SQLite (実行履歴)

## 連携するエージェント
- **NEWS-Logic**: スケジュール実行ロジック
- **NEWS-Analyzer**: AI分析トリガー
- **NEWS-ReportGen**: レポート生成スケジュール
- **NEWS-Monitor**: スケジュール実行監視
- **NEWS-Webhook**: イベントトリガー連携

## KPI目標
- **スケジュール実行精度**: 99.9%以上
- **実行遅延**: 30秒以内
- **緊急配信応答時間**: 1分以内
- **タスク失敗率**: 0.1%未満
- **システム可用性**: 99.5%以上

## 主要機能

### 動的スケジュール調整
```python
class DynamicScheduler:
    async def adjust_schedule_based_on_activity(self):
        """アクティビティベースのスケジュール調整"""
        # ニュース活動度分析
        activity_level = await self.analyze_news_activity()
        
        if activity_level > 8:  # 高活動期
            # 収集頻度を増加
            self.add_temporary_schedule("14:00", duration_hours=2)
            self.add_temporary_schedule("16:00", duration_hours=2)
        elif activity_level < 3:  # 低活動期
            # 一部スケジュールを休止
            self.pause_schedule("12:00", duration_hours=1)
```

### バッチ処理管理
- 日次データクリーンアップ
- 週次統計生成
- 月次レポート作成
- システム最適化タスク

### 監視・アラート
- スケジュール実行状況監視
- 失敗時の自動リトライ
- 実行時間監視
- リソース使用量チェック

## エラー処理・復旧
- 実行失敗時の自動リトライ
- 部分的な処理継続
- フォールバック処理
- 緊急時の手動実行機能

## 成果物
- スケジュール実行エンジン
- Windows タスク設定
- 緊急配信システム
- 実行履歴管理
- 監視ダッシュボード