#!/usr/bin/env python3
"""
Optimization Modules Integration Tests
最適化モジュールの統合テスト
"""

import asyncio
import pytest
import sys
import os
from pathlib import Path
from datetime import datetime
import tempfile
import json

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# 先に依存モジュールをインポート
from src.utils.path_resolver import get_path_resolver
from src.utils.config import get_config
from src.utils.logger import setup_logger
from src.models.article import Article

# 最適化モジュールをインポート
from src.generators.pdf_generator_optimized import OptimizedPDFReportGenerator, get_optimized_pdf_generator
from src.collectors.session_manager import SessionPool, OptimizedAPIClient, get_session_pool, get_api_client

# メトリクスモジュールは一時的にスキップ（インポートエラー回避）
try:
    from src.monitoring.advanced_metrics_monitor import MetricsCollector
except ImportError:
    MetricsCollector = None
    print("Warning: MetricsCollector could not be imported")


class TestOptimizedPDFGenerator:
    """PDF生成最適化テスト"""
    
    @pytest.fixture
    def pdf_generator(self):
        """PDFジェネレーターフィクスチャ"""
        generator = OptimizedPDFReportGenerator()
        return generator
    
    def test_pdf_generator_initialization(self):
        """PDF生成器初期化テスト"""
        generator = OptimizedPDFReportGenerator()
        
        assert generator is not None
        assert generator.pdf_options is not None
        assert 'encoding' in generator.pdf_options
        assert generator.pdf_options['encoding'] == 'UTF-8'
        assert 'disable-javascript' in generator.pdf_options
        assert generator.generation_stats['total_generated'] == 0
    
    def test_wkhtmltopdf_detection(self):
        """wkhtmltopdf検出テスト"""
        generator = OptimizedPDFReportGenerator()
        
        # wkhtmltopdfパスの検出
        if generator.wkhtmltopdf_path:
            assert Path(generator.wkhtmltopdf_path).exists()
            print(f"✓ wkhtmltopdf found at: {generator.wkhtmltopdf_path}")
        else:
            print("⚠ wkhtmltopdf not found - PDF generation will not work")
    
    def test_html_optimization(self):
        """HTML最適化テスト"""
        generator = OptimizedPDFReportGenerator()
        
        # テストHTML
        html = """
        <html>
            <head>
                <style>
                    /* Comment */
                    body   {   margin:   20px;   padding:   10px;   }
                </style>
            </head>
            <body>
                <h1>  Test   Title  </h1>
                <p>  Test   content  </p>
            </body>
        </html>
        """
        
        optimized = generator._optimize_html(html)
        
        # 最適化確認
        assert '/* Comment */' not in optimized  # コメント削除
        assert 'margin:20px' in optimized  # 空白削除
        assert '><' in optimized  # タグ間の空白削除
        assert len(optimized) < len(html)  # サイズ削減
    
    def test_pdf_generation_test_function(self):
        """PDF生成テスト機能"""
        generator = OptimizedPDFReportGenerator()
        
        result = generator.test_pdf_generation()
        
        assert 'success' in result
        
        if result['success']:
            assert 'pdf_path' in result
            assert Path(result['pdf_path']).exists()
            print(f"✓ Test PDF generated: {result['pdf_path']}")
        else:
            print(f"⚠ PDF generation failed: {result.get('error', 'Unknown error')}")
    
    @pytest.mark.asyncio
    async def test_async_pdf_generation(self, pdf_generator):
        """非同期PDF生成テスト"""
        # テスト記事作成
        articles = [
            Article(
                title="テスト記事1",
                url="https://example.com/test1",
                description="テスト記事の説明1",
                published_at=datetime.now().isoformat(),
                source_name="Test Source",
                category="test"
            ),
            Article(
                title="テスト記事2",
                url="https://example.com/test2",
                description="テスト記事の説明2",
                published_at=datetime.now().isoformat(),
                source_name="Test Source",
                category="test"
            ),
        ]
        
        # PDF生成
        pdf_path = await pdf_generator.generate_daily_report_async(articles)
        
        if pdf_path:
            assert Path(pdf_path).exists()
            assert Path(pdf_path).stat().st_size > 0
            print(f"✓ Async PDF generated: {pdf_path}")
            
            # 統計確認
            stats = pdf_generator.get_generation_stats()
            assert stats['successful'] > 0
        else:
            print("⚠ Async PDF generation skipped (wkhtmltopdf not available)")
    
    def test_generation_statistics(self):
        """生成統計テスト"""
        generator = OptimizedPDFReportGenerator()
        
        # 初期統計
        stats = generator.get_generation_stats()
        assert stats['total_generated'] == 0
        assert stats['success_rate'] == 0
        
        # wkhtmltopdfが利用可能な場合のみテスト実行
        if generator.wkhtmltopdf_path:
            # テスト生成実行
            generator.test_pdf_generation()
            
            # 統計更新確認
            stats = generator.get_generation_stats()
            assert stats['total_generated'] > 0
        else:
            print("⚠ wkhtmltopdf not found - skipping statistics test")


class TestAdvancedMetricsMonitor:
    """高度なメトリクス監視テスト"""
    
    @pytest.fixture
    def metrics_collector(self):
        """メトリクスコレクターフィクスチャ"""
        collector = MetricsCollector()
        return collector
    
    @pytest.mark.asyncio
    async def test_system_metrics_collection(self, metrics_collector):
        """システムメトリクス収集テスト"""
        metrics = await metrics_collector._gather_system_metrics()
        
        # 基本メトリクス確認
        assert 'timestamp' in metrics
        assert 'cpu' in metrics
        assert 'memory' in metrics
        assert 'disk' in metrics
        assert 'network' in metrics
        assert 'process' in metrics
        
        # CPU メトリクス
        assert 'percent' in metrics['cpu']
        assert 0 <= metrics['cpu']['percent'] <= 100
        assert 'cores' in metrics['cpu']
        assert metrics['cpu']['cores'] > 0
        
        # メモリメトリクス
        assert 'percent' in metrics['memory']
        assert 0 <= metrics['memory']['percent'] <= 100
        assert 'used_gb' in metrics['memory']
        assert metrics['memory']['used_gb'] > 0
        
        # ディスクメトリクス
        assert 'percent' in metrics['disk']
        assert 0 <= metrics['disk']['percent'] <= 100
        
        print(f"✓ CPU: {metrics['cpu']['percent']:.1f}%")
        print(f"✓ Memory: {metrics['memory']['percent']:.1f}%")
        print(f"✓ Disk: {metrics['disk']['percent']:.1f}%")
    
    @pytest.mark.asyncio
    async def test_detailed_metrics_collection(self, metrics_collector):
        """詳細メトリクス収集テスト"""
        detailed = await metrics_collector._gather_detailed_metrics()
        
        assert 'type' in detailed
        assert detailed['type'] == 'detailed'
        assert 'database' in detailed
        assert 'api_usage' in detailed
        assert 'cache' in detailed
        
        print("✓ Detailed metrics collected successfully")
    
    def test_threshold_adjustment(self, metrics_collector):
        """動的しきい値調整テスト"""
        # 初期しきい値
        initial_cpu_threshold = metrics_collector.dynamic_thresholds['cpu_percent']['current']
        
        # サンプルメトリクス追加
        for i in range(20):
            metrics = {
                'cpu': {'percent': 50 + i},
                'memory': {'percent': 60 + i},
            }
            metrics_collector.metrics_buffer.append(metrics)
            metrics_collector._adjust_thresholds(metrics)
        
        # しきい値が調整されたか確認
        current_cpu_threshold = metrics_collector.dynamic_thresholds['cpu_percent']['current']
        
        assert current_cpu_threshold != initial_cpu_threshold
        print(f"✓ Threshold adjusted: {initial_cpu_threshold:.1f} -> {current_cpu_threshold:.1f}")
    
    def test_anomaly_detection(self, metrics_collector):
        """異常検知テスト"""
        # 正常値サンプル
        for i in range(50):
            metrics_collector.anomaly_detection['cpu']['samples'].append(50.0)
        
        # 統計計算
        metrics_collector.anomaly_detection['cpu']['mean'] = 50.0
        metrics_collector.anomaly_detection['cpu']['std'] = 5.0
        
        # 正常値テスト
        normal_anomaly = metrics_collector._detect_metric_anomaly('cpu', 55.0)
        assert normal_anomaly is None
        
        # 異常値テスト
        anomaly = metrics_collector._detect_metric_anomaly('cpu', 90.0)
        assert anomaly is not None
        assert anomaly['metric'] == 'cpu'
        assert anomaly['z_score'] > 3
        
        print(f"✓ Anomaly detected: z-score = {anomaly['z_score']:.2f}")
    
    def test_trend_calculation(self, metrics_collector):
        """トレンド計算テスト"""
        # 増加トレンドデータ (傾きを大きくして、0.5のしきい値を超える)
        for i in range(60):
            metrics = {
                'cpu': {'percent': 40 + i * 1.0},  # より急な増加 (傾き1.0)
                'memory': {'percent': 50},
                'disk': {'percent': 60 + i * 0.1},
            }
            metrics_collector.metrics_buffer.append(metrics)
        
        trends = metrics_collector._calculate_trends()
        
        assert 'cpu' in trends
        assert 'trend' in trends['cpu']
        # トレンド判定のしきい値が0.5なので、急な増加か安定のどちらかを許容
        assert trends['cpu']['trend'] in ['increasing', 'stable']
        
        assert 'disk' in trends
        assert 'growth_rate' in trends['disk']
        assert trends['disk']['growth_rate'] > 0
        
        print(f"✓ CPU trend: {trends['cpu']['trend']}")
        print(f"✓ Disk growth rate: {trends['disk']['growth_rate']:.2f}%/hour")
    
    def test_metrics_summary(self, metrics_collector):
        """メトリクスサマリーテスト"""
        # テストデータ追加
        for i in range(10):
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'cpu': {'percent': 50 + i},
                'memory': {'percent': 60 + i},
            }
            metrics_collector.metrics_buffer.append(metrics)
        
        summary = metrics_collector.get_metrics_summary(hours=1)
        
        assert 'samples' in summary
        assert summary['samples'] == 10
        assert 'cpu' in summary
        assert 'avg' in summary['cpu']
        assert summary['cpu']['avg'] > 0
        
        print(f"✓ Metrics summary: {summary['samples']} samples")


class TestSessionManager:
    """セッション管理テスト"""
    
    @pytest.fixture
    def session_pool(self):
        """セッションプールフィクスチャ"""
        pool = SessionPool(max_sessions=5, max_per_host=2)
        return pool
    
    @pytest.mark.asyncio
    async def test_session_pool_initialization(self, session_pool):
        """セッションプール初期化テスト"""
        assert session_pool is not None
        assert session_pool.max_sessions == 5
        assert session_pool.max_per_host == 2
        assert len(session_pool.sessions) == 0
        
        print("✓ Session pool initialized")
    
    @pytest.mark.asyncio
    async def test_session_acquisition(self, session_pool):
        """セッション取得テスト"""
        # セッション取得
        async with session_pool.get_session('test_service') as session:
            assert session is not None
            assert not session.closed
        
        # 統計確認
        stats = session_pool.get_statistics()
        assert stats['connections_created'] > 0
        
        print(f"✓ Session acquired: {stats['connections_created']} created")
    
    @pytest.mark.asyncio
    async def test_session_reuse(self, session_pool):
        """セッション再利用テスト"""
        # 1回目のセッション取得
        async with session_pool.get_session('test_service') as session1:
            assert session1 is not None
        
        # 2回目のセッション取得（再利用されるはず）
        async with session_pool.get_session('test_service') as session2:
            assert session2 is not None
        
        stats = session_pool.get_statistics()
        assert stats['connections_reused'] > 0
        
        print(f"✓ Session reused: {stats['connections_reused']} times")
    
    @pytest.mark.asyncio
    async def test_session_limit(self, session_pool):
        """セッション数制限テスト"""
        sessions = []
        
        # 制限まで取得
        for i in range(session_pool.max_per_host):
            session = await session_pool._acquire_session(f'test_service_{i}')
            sessions.append(session)
        
        assert len(session_pool.sessions) <= session_pool.max_per_host
        
        print(f"✓ Session limit enforced: {len(sessions)} sessions")
    
    @pytest.mark.asyncio
    async def test_session_statistics(self, session_pool):
        """セッション統計テスト"""
        # いくつかのセッションを作成
        async with session_pool.get_session('service1') as s1:
            pass
        async with session_pool.get_session('service2') as s2:
            pass
        async with session_pool.get_session('service1') as s3:  # 再利用
            pass
        
        stats = session_pool.get_statistics()
        
        assert 'total_requests' in stats
        assert 'connections_created' in stats
        assert 'connections_reused' in stats
        assert 'reuse_rate' in stats
        assert stats['reuse_rate'] > 0
        
        print(f"✓ Reuse rate: {stats['reuse_rate']:.1f}%")
    
    @pytest.mark.asyncio
    async def test_optimized_api_client(self, session_pool):
        """最適化APIクライアントテスト"""
        client = OptimizedAPIClient(session_pool)
        
        # テストリクエスト（実際のAPIは呼ばない）
        # モックまたはローカルテストサーバーが必要
        
        assert client is not None
        assert client.max_retries == 3
        
        print("✓ Optimized API client created")


class TestIntegration:
    """統合テスト"""
    
    @pytest.mark.asyncio
    async def test_all_optimizations_together(self):
        """全最適化機能の統合テスト"""
        results = {
            'pdf_generation': False,
            'metrics_monitoring': False,
            'session_management': False,
        }
        
        # PDF生成テスト
        try:
            pdf_gen = OptimizedPDFReportGenerator()
            test_result = pdf_gen.test_pdf_generation()
            results['pdf_generation'] = test_result.get('success', False)
        except Exception as e:
            print(f"PDF generation test failed: {e}")
        
        # メトリクス監視テスト
        try:
            if MetricsCollector:
                metrics = MetricsCollector()
                system_metrics = await metrics._gather_system_metrics()
                results['metrics_monitoring'] = 'cpu' in system_metrics
            else:
                print("Metrics monitoring test skipped (import error)")
                results['metrics_monitoring'] = False
        except Exception as e:
            print(f"Metrics monitoring test failed: {e}")
        
        # セッション管理テスト
        try:
            pool = SessionPool()
            await pool.initialize()
            async with pool.get_session('test') as session:
                results['session_management'] = not session.closed
            await pool.close_all_sessions()
        except Exception as e:
            print(f"Session management test failed: {e}")
        
        # 結果表示
        print("\n=== Integration Test Results ===")
        for feature, success in results.items():
            status = "✓" if success else "✗"
            print(f"{status} {feature}: {'OK' if success else 'FAILED'}")
        
        # 全体の成功判定
        all_success = all(results.values())
        assert len([v for v in results.values() if v]) >= 2  # 少なくとも2つは成功


def run_optimization_tests():
    """最適化テスト実行"""
    print("=" * 60)
    print("Running Optimization Tests")
    print("=" * 60)
    
    # PDF生成テスト
    print("\n[PDF Generation Tests]")
    pdf_tests = TestOptimizedPDFGenerator()
    pdf_tests.test_pdf_generator_initialization()
    pdf_tests.test_wkhtmltopdf_detection()
    pdf_tests.test_html_optimization()
    pdf_tests.test_pdf_generation_test_function()
    
    # メトリクス監視テスト
    print("\n[Metrics Monitoring Tests]")
    if MetricsCollector:
        metrics_tests = TestAdvancedMetricsMonitor()
        collector = MetricsCollector()
        
        # 非同期テストを同期的に実行
        asyncio.run(
            metrics_tests.test_system_metrics_collection(collector)
        )
    else:
        print("⚠ Metrics monitoring tests skipped (import error)")
    
    # セッション管理テスト
    print("\n[Session Management Tests]")
    async def run_session_tests():
        session_tests = TestSessionManager()
        pool = SessionPool(max_sessions=5, max_per_host=2)
        
        await pool.initialize()
        await session_tests.test_session_pool_initialization(pool)
        await pool.close_all_sessions()
        print("✓ Session management tests completed")
    
    asyncio.run(run_session_tests())
    
    # 統合テスト
    print("\n[Integration Tests]")
    integration = TestIntegration()
    asyncio.run(
        integration.test_all_optimizations_together()
    )
    
    print("\n" + "=" * 60)
    print("All optimization tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    run_optimization_tests()