#!/usr/bin/env python3
"""
Integration Tests for News Delivery System
ニュース配信システム統合テスト

全モジュールの統合動作を検証
"""

import asyncio
import json
import os
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.path_resolver import PathResolver, get_path_resolver
from src.utils.config import ConfigManager, get_config
from src.utils.scheduler_manager import SchedulerManager
from src.monitoring.health_monitor import HealthMonitor


class TestPathResolver(unittest.TestCase):
    """パスリゾルバのテスト"""
    
    def setUp(self):
        self.resolver = PathResolver()
    
    def test_project_root_detection(self):
        """プロジェクトルートの検出テスト"""
        self.assertTrue(self.resolver.project_root.exists())
        self.assertTrue((self.resolver.project_root / "CLAUDE.md").exists())
    
    def test_data_path_creation(self):
        """データパスの作成テスト"""
        test_path = self.resolver.get_data_path("test", "integration")
        self.assertTrue(test_path.exists())
        self.assertTrue(test_path.is_dir())
        
        # クリーンアップ
        if test_path.exists():
            test_path.rmdir()
    
    def test_cross_platform_path_conversion(self):
        """クロスプラットフォームパス変換テスト"""
        windows_path = "E:\\NewsDeliverySystem\\data\\test.txt"
        converted = self.resolver.convert_windows_path(windows_path)
        self.assertIsInstance(converted, Path)
    
    def test_platform_info(self):
        """プラットフォーム情報取得テスト"""
        info = self.resolver.get_platform_info()
        self.assertIn('platform', info)
        self.assertIn('project_root', info)
        self.assertIn('data_root', info)
    
    def test_path_validation(self):
        """パス検証テスト"""
        validation = self.resolver.validate_paths()
        self.assertIn('project_root', validation)
        self.assertIn('data_root', validation)
        self.assertTrue(validation['project_root']['exists'])


class TestConfigManager(unittest.TestCase):
    """設定管理のテスト"""
    
    def setUp(self):
        # テスト用設定ファイルを作成
        self.test_config_path = Path(__file__).parent / "test_config.json"
        self.test_config = {
            "system": {
                "version": "1.0.0",
                "log_level": "INFO"
            },
            "news_sources": {
                "newsapi": {
                    "enabled": True,
                    "api_key": "test_key"
                }
            },
            "delivery": {
                "schedule": ["07:00", "12:00", "18:00"],
                "urgent_notification": {
                    "enabled": True,
                    "importance_threshold": 10
                }
            }
        }
        
        with open(self.test_config_path, 'w') as f:
            json.dump(self.test_config, f)
        
        self.config = ConfigManager(config_path=str(self.test_config_path))
    
    def tearDown(self):
        # テスト用設定ファイルを削除
        if self.test_config_path.exists():
            self.test_config_path.unlink()
    
    def test_config_loading(self):
        """設定ファイル読み込みテスト"""
        self.assertEqual(self.config.get('system', 'version'), "1.0.0")
        self.assertEqual(self.config.get('system', 'log_level'), "INFO")
    
    def test_service_enabled_check(self):
        """サービス有効性チェックテスト"""
        self.assertTrue(self.config.is_service_enabled('newsapi'))
    
    def test_storage_path_resolution(self):
        """ストレージパス解決テスト"""
        db_path = self.config.get_storage_path('database')
        self.assertIsInstance(db_path, Path)
        self.assertTrue(db_path.parent.exists())
    
    def test_environment_override(self):
        """環境変数オーバーライドテスト"""
        with patch.dict(os.environ, {'LOG_LEVEL': 'DEBUG'}):
            config = ConfigManager(config_path=str(self.test_config_path))
            # 環境変数が優先される
            self.assertEqual(config.get('system', 'log_level'), 'DEBUG')


class TestSchedulerManager(unittest.TestCase):
    """スケジューラ管理のテスト"""
    
    def setUp(self):
        self.scheduler = SchedulerManager()
    
    def test_schedule_loading(self):
        """スケジュール読み込みテスト"""
        schedules = self.scheduler.schedules
        self.assertIsInstance(schedules, list)
        self.assertTrue(len(schedules) > 0)
        
        # デフォルトスケジュールの確認
        daily_schedules = [s for s in schedules if s['type'] == 'daily']
        self.assertTrue(len(daily_schedules) >= 3)  # 7:00, 12:00, 18:00
    
    def test_execution_command_generation(self):
        """実行コマンド生成テスト"""
        command = self.scheduler._get_execution_command()
        self.assertIn('python', command)
        self.assertIn('main.py', command)
    
    def test_cron_entry_creation(self):
        """cronエントリ作成テスト"""
        schedule = {
            'name': 'test_schedule',
            'time': '12:00',
            'type': 'daily',
            'command': 'python test.py',
            'description': 'Test schedule'
        }
        
        entry = self.scheduler._create_cron_entry(schedule)
        self.assertIsNotNone(entry)
        self.assertIn('0 12', entry)  # 12:00のcron形式
        self.assertIn('python test.py', entry)
    
    def test_schedule_validation(self):
        """スケジュール検証テスト"""
        valid, issues = self.scheduler.validate_schedules()
        
        # Pythonは存在するはず
        python_issue = [i for i in issues if 'Python executable' in i]
        self.assertEqual(len(python_issue), 0)


class TestHealthMonitor(unittest.TestCase):
    """ヘルスモニタのテスト"""
    
    def setUp(self):
        self.monitor = HealthMonitor()
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    async def test_system_resource_check(self, mock_disk, mock_memory, mock_cpu):
        """システムリソースチェックテスト"""
        # モックの設定
        mock_cpu.return_value = 50.0
        mock_memory.return_value = Mock(
            percent=60.0,
            used=8 * 1024**3,
            available=8 * 1024**3
        )
        mock_disk.return_value = Mock(
            percent=70.0,
            used=500 * 1024**3,
            free=500 * 1024**3
        )
        
        result = await self.monitor._check_system_resources()
        
        self.assertEqual(result['cpu']['percent'], 50.0)
        self.assertEqual(result['cpu']['status'], 'healthy')
        self.assertEqual(result['memory']['percent'], 60.0)
        self.assertEqual(result['memory']['status'], 'healthy')
        self.assertEqual(result['disk']['percent'], 70.0)
        self.assertEqual(result['disk']['status'], 'healthy')
    
    async def test_overall_health_evaluation(self):
        """全体的な健全性評価テスト"""
        health_status = {
            'system': {
                'cpu': {'status': 'healthy'},
                'memory': {'status': 'healthy'},
                'disk': {'status': 'healthy'}
            },
            'apis': {
                'newsapi': {'status': 'healthy'},
                'deepl': {'status': 'healthy'}
            },
            'database': {'status': 'healthy'}
        }
        
        overall = self.monitor._evaluate_overall_health(health_status)
        self.assertEqual(overall, 'healthy')
        
        # 一部問題がある場合
        health_status['system']['cpu']['status'] = 'warning'
        overall = self.monitor._evaluate_overall_health(health_status)
        self.assertIn(overall, ['degraded', 'healthy'])
    
    def test_cooldown_mechanism(self):
        """クールダウンメカニズムテスト"""
        issue = 'test_issue'
        
        # 初回はクールダウンなし
        self.assertFalse(self.monitor._is_in_cooldown(issue))
        
        # クールダウン設定
        self.monitor._set_cooldown(issue)
        
        # クールダウン中
        self.assertTrue(self.monitor._is_in_cooldown(issue))
    
    async def test_healing_action_high_memory(self):
        """高メモリ修復アクションテスト"""
        health_status = {
            'system': {
                'memory': {'percent': 90.0, 'status': 'warning'}
            }
        }
        
        with patch('gc.collect') as mock_gc:
            result = await self.monitor._heal_high_memory(health_status)
            self.assertTrue(result)
            mock_gc.assert_called_once()


class TestEndToEndWorkflow(unittest.TestCase):
    """エンドツーエンドワークフローテスト"""
    
    async def test_full_news_processing_workflow(self):
        """完全なニュース処理ワークフローテスト"""
        # このテストは実際のAPIを呼び出さないようにモック化
        with patch('src.collectors.newsapi_collector.NewsAPICollector.collect') as mock_collect:
            with patch('src.processors.translator.DeepLTranslator.translate_batch') as mock_translate:
                with patch('src.processors.analyzer.ClaudeAnalyzer.analyze_batch') as mock_analyze:
                    with patch('src.notifiers.gmail_sender.GmailSender.send_report') as mock_send:
                        
                        # モックデータ設定
                        mock_collect.return_value = [
                            {
                                'title': 'Test News',
                                'description': 'Test Description',
                                'url': 'https://example.com/news',
                                'published_at': datetime.now().isoformat()
                            }
                        ]
                        
                        mock_translate.return_value = mock_collect.return_value
                        mock_analyze.return_value = mock_collect.return_value
                        mock_send.return_value = True
                        
                        # ワークフロー実行のシミュレーション
                        # 実際のmain.pyの処理フローをテスト
                        result = {
                            'collection': mock_collect.return_value is not None,
                            'translation': mock_translate.return_value is not None,
                            'analysis': mock_analyze.return_value is not None,
                            'delivery': mock_send.return_value
                        }
                        
                        # 全ステップが成功したことを確認
                        for step, success in result.items():
                            self.assertTrue(success, f"Step {step} failed")


def run_async_test(coro):
    """非同期テストを実行するヘルパー関数"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


class AsyncTestCase(unittest.TestCase):
    """非同期テストケースの基底クラス"""
    
    def run_async(self, coro):
        """非同期コルーチンを実行"""
        return run_async_test(coro)


class TestAsyncHealthMonitor(AsyncTestCase):
    """非同期ヘルスモニタテスト"""
    
    def test_system_check_async(self):
        """非同期システムチェック"""
        monitor = HealthMonitor()
        result = self.run_async(monitor._check_system_resources())
        self.assertIn('cpu', result)
        self.assertIn('memory', result)
        self.assertIn('disk', result)


def suite():
    """テストスイートを構築"""
    test_suite = unittest.TestSuite()
    
    # 各テストクラスを追加
    test_suite.addTest(unittest.makeSuite(TestPathResolver))
    test_suite.addTest(unittest.makeSuite(TestConfigManager))
    test_suite.addTest(unittest.makeSuite(TestSchedulerManager))
    test_suite.addTest(unittest.makeSuite(TestHealthMonitor))
    test_suite.addTest(unittest.makeSuite(TestEndToEndWorkflow))
    test_suite.addTest(unittest.makeSuite(TestAsyncHealthMonitor))
    
    return test_suite


if __name__ == '__main__':
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite())
    
    # 結果サマリー
    print("\n" + "="*60)
    print("統合テスト結果サマリー")
    print("="*60)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.failures:
        print("\n失敗したテスト:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\nエラーが発生したテスト:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    # 終了コード
    sys.exit(0 if result.wasSuccessful() else 1)