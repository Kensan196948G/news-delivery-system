# NEWS-E2E - E2Eテストエージェント

## エージェント概要
ニュース配信システムのエンドツーエンドテスト、統合テスト、システム全体の動作検証を専門とするエージェント。

## 役割と責任
- E2Eテストシナリオ設計・実行
- システム統合テスト
- ユーザーストーリーベーステスト
- 本番環境相当テスト
- システム全体の品質保証

## 主要業務

### E2Eテストシナリオ実行
```python
import pytest
import asyncio
from datetime import datetime
from typing import Dict, List

class E2ETestRunner:
    def __init__(self):
        self.test_env = TestEnvironment()
        self.data_validator = DataValidator()
        self.notification_checker = NotificationChecker()
        
    @pytest.mark.e2e
    async def test_complete_news_delivery_flow(self):
        """完全なニュース配信フロー E2E テスト"""
        
        # フェーズ 1: システム初期化
        await self.test_env.setup()
        
        # フェーズ 2: ニュース収集
        collection_start = datetime.now()
        
        news_system = NewsDeliverySystem()
        
        # 実際のAPIを使用したニュース収集
        collected_articles = await news_system.collect_news()
        
        collection_time = (datetime.now() - collection_start).total_seconds()
        
        # 検証: 収集結果
        assert len(collected_articles) > 0, "記事が収集されませんでした"
        assert collection_time < 300, f"収集時間が長すぎます: {collection_time}秒"
        
        # フェーズ 3: 翻訳処理
        translation_start = datetime.now()
        
        translated_articles = await news_system.translate_articles(collected_articles)
        
        translation_time = (datetime.now() - translation_start).total_seconds()
        
        # 検証: 翻訳結果
        english_articles = [a for a in collected_articles if a.needs_translation]
        translated_count = sum(1 for a in translated_articles if a.translated_title)
        
        assert translated_count == len(english_articles), "翻訳されていない記事があります"
        assert translation_time < 120, f"翻訳時間が長すぎます: {translation_time}秒"
        
        # フェーズ 4: AI分析
        analysis_start = datetime.now()
        
        analyzed_articles = await news_system.analyze_articles(translated_articles)
        
        analysis_time = (datetime.now() - analysis_start).total_seconds()
        
        # 検証: AI分析結果
        analyzed_count = sum(1 for a in analyzed_articles if a.ai_analysis)
        assert analyzed_count >= len(analyzed_articles) * 0.8, "AI分析率が低すぎます"
        assert analysis_time < 300, f"AI分析時間が長すぎます: {analysis_time}秒"
        
        # フェーズ 5: レポート生成
        report_start = datetime.now()
        
        html_report = await news_system.generate_html_report(analyzed_articles)
        pdf_report = await news_system.generate_pdf_report(html_report)
        
        report_time = (datetime.now() - report_start).total_seconds()
        
        # 検証: レポート生成
        assert html_report is not None, "HTMLレポートが生成されませんでした"
        assert len(html_report) > 1000, "HTMLレポートが短すぎます"
        assert pdf_report is not None, "PDFレポートが生成されませんでした"
        assert report_time < 120, f"レポート生成時間が長すぎます: {report_time}秒"
        
        # フェーズ 6: メール配信
        delivery_start = datetime.now()
        
        delivery_result = await news_system.send_email_delivery(
            html_content=html_report,
            pdf_path=pdf_report,
            recipient="test@example.com"
        )
        
        delivery_time = (datetime.now() - delivery_start).total_seconds()
        
        # 検証: メール配信
        assert delivery_result.success, f"メール配信に失敗: {delivery_result.error}"
        assert delivery_time < 60, f"配信時間が長すぎます: {delivery_time}秒"
        
        # フェーズ 7: データベース保存検証
        await self._verify_database_storage(analyzed_articles)
        
        # フェーズ 8: 全体パフォーマンス検証
        total_time = collection_time + translation_time + analysis_time + report_time + delivery_time
        assert total_time < 600, f"総実行時間が長すぎます: {total_time}秒 (目標: 10分以内)"
        
        # クリーンアップ
        await self.test_env.cleanup()
```

### 緊急配信E2Eテスト
```python
@pytest.mark.e2e
@pytest.mark.priority_high
async def test_emergency_delivery_flow(self):
    """緊急配信フローのE2Eテスト"""
    
    # 高重要度記事データ作成
    critical_article = self._create_critical_article()
    
    # システムへ記事投入
    news_system = NewsDeliverySystem()
    
    # 緊急配信トリガー監視開始
    emergency_monitor = EmergencyDeliveryMonitor()
    await emergency_monitor.start_monitoring()
    
    # 記事処理実行
    processed_articles = await news_system.process_articles([critical_article])
    
    # 緊急配信が自動トリガーされることを検証
    emergency_delivery = await emergency_monitor.wait_for_emergency_delivery(timeout=60)
    
    assert emergency_delivery is not None, "緊急配信がトリガーされませんでした"
    assert emergency_delivery.article_ids == [critical_article.id]
    assert emergency_delivery.priority == "urgent"
    assert emergency_delivery.delivery_time < 60, "緊急配信が1分以内に実行されませんでした"
    
def _create_critical_article(self) -> Article:
    """重要度10の記事作成"""
    return Article(
        id="critical_test_001",
        title="CRITICAL: Zero-day vulnerability discovered in Windows",
        content="A critical zero-day vulnerability has been discovered...",
        url="https://security.test/critical-vuln",
        category="security",
        importance_score=10,
        cvss_score=9.8,
        published_at=datetime.now(),
        source_name="Security Test"
    )
```

### APIエンドポイント統合テスト
```python
class APIIntegrationTester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.client = httpx.AsyncClient()
        
    @pytest.mark.e2e
    async def test_api_workflow_integration(self):
        """APIワークフロー統合テスト"""
        
        # 1. システムステータス確認
        status_response = await self.client.get(f"{self.base_url}/api/health")
        assert status_response.status_code == 200
        
        health_data = status_response.json()
        assert health_data["status"] == "healthy"
        assert all(service["status"] == "up" for service in health_data["services"])
        
        # 2. ニュース収集トリガー
        collection_response = await self.client.post(
            f"{self.base_url}/api/news/collect",
            json={"categories": ["tech", "security"], "count": 10}
        )
        assert collection_response.status_code == 202
        
        job_id = collection_response.json()["job_id"]
        
        # 3. 収集状況確認（ポーリング）
        collection_completed = False
        for attempt in range(30):  # 5分間監視
            status_response = await self.client.get(f"{self.base_url}/api/jobs/{job_id}")
            status_data = status_response.json()
            
            if status_data["status"] == "completed":
                collection_completed = True
                break
            elif status_data["status"] == "failed":
                pytest.fail(f"ニュース収集ジョブが失敗: {status_data.get('error')}")
            
            await asyncio.sleep(10)
        
        assert collection_completed, "ニュース収集が時間内に完了しませんでした"
        
        # 4. 収集された記事取得
        articles_response = await self.client.get(f"{self.base_url}/api/articles?job_id={job_id}")
        assert articles_response.status_code == 200
        
        articles_data = articles_response.json()
        assert len(articles_data["articles"]) > 0, "記事が収集されませんでした"
        
        # 5. レポート生成リクエスト
        report_response = await self.client.post(
            f"{self.base_url}/api/reports/generate",
            json={"job_id": job_id, "format": ["html", "pdf"]}
        )
        assert report_response.status_code == 202
        
        report_job_id = report_response.json()["job_id"]
        
        # 6. レポート生成完了待機
        report_completed = False
        for attempt in range(20):  # 3分間監視
            report_status_response = await self.client.get(f"{self.base_url}/api/jobs/{report_job_id}")
            report_status_data = report_status_response.json()
            
            if report_status_data["status"] == "completed":
                report_completed = True
                break
            elif report_status_data["status"] == "failed":
                pytest.fail(f"レポート生成が失敗: {report_status_data.get('error')}")
            
            await asyncio.sleep(9)
        
        assert report_completed, "レポート生成が時間内に完了しませんでした"
        
        # 7. 配信実行
        delivery_response = await self.client.post(
            f"{self.base_url}/api/delivery/send",
            json={
                "report_job_id": report_job_id,
                "recipients": ["test@example.com"],
                "priority": "normal"
            }
        )
        assert delivery_response.status_code == 200
        
        delivery_result = delivery_response.json()
        assert delivery_result["status"] == "sent"
        assert "delivery_id" in delivery_result
```

## 使用する技術・ツール
- **テストフレームワーク**: pytest, pytest-asyncio
- **APIテスト**: httpx, aiohttp
- **データベース**: SQLite テスト用DB
- **モック**: aioresponses, pytest-mock
- **監視**: prometheus_client
- **レポート**: allure-pytest

## 連携するエージェント
- **NEWS-Tester**: 単体テスト結果活用
- **NEWS-QA**: 品質基準適用
- **NEWS-Monitor**: システム監視連携
- **NEWS-CI**: CI/CD統合
- **NEWS-Security**: セキュリティテスト

## KPI目標
- **E2Eテスト成功率**: 98%以上
- **テスト実行時間**: 15分以内
- **システム可用性**: 99.5%以上
- **エラー検出率**: 95%以上
- **回帰テスト網羅性**: 90%以上

## テストシナリオ

### 基本フローテスト
- 標準的な配信フロー
- 各種カテゴリの記事処理
- 定時配信シナリオ
- エラー回復シナリオ

### 例外処理テスト
- API制限到達時の動作
- ネットワーク障害時の回復
- データベース障害対応
- 外部サービス障害対応

### パフォーマンステスト
- 大量記事処理性能
- 同時配信処理性能
- メモリ使用量監視
- レスポンス時間測定

## 環境管理
- テスト環境自動構築
- テストデータ管理
- 設定管理
- クリーンアップ処理

## 成果物
- E2Eテストスイート
- 統合テストシナリオ
- テスト実行レポート
- パフォーマンステスト結果
- システム品質証明書