# NEWS-QA - 品質保証エージェント

## エージェント概要
ニュース配信システムの品質保証、品質管理、品質メトリクス監視を専門とするエージェント。

## 役割と責任
- 品質基準設定・管理
- コード品質監視
- データ品質検証
- 配信品質チェック
- 品質改善提案

## 主要業務

### データ品質検証
```python
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class QualityMetrics:
    completeness: float  # 完全性 (0-1)
    accuracy: float      # 正確性 (0-1)
    consistency: float   # 一貫性 (0-1)
    validity: float      # 妥当性 (0-1)
    uniqueness: float    # 一意性 (0-1)
    overall_score: float # 総合品質スコア (0-100)

class DataQualityChecker:
    def __init__(self):
        self.quality_thresholds = {
            'completeness': 0.95,
            'accuracy': 0.90,
            'consistency': 0.92,
            'validity': 0.88,
            'uniqueness': 0.98
        }
        
    async def validate_article_data(self, articles: List[Article]) -> QualityMetrics:
        """記事データ品質検証"""
        total_articles = len(articles)
        
        # 完全性チェック
        completeness_scores = []
        for article in articles:
            required_fields = ['title', 'url', 'content', 'published_at', 'source_name']
            filled_fields = sum(1 for field in required_fields if getattr(article, field))
            completeness_scores.append(filled_fields / len(required_fields))
        
        completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0
        
        # 正確性チェック（翻訳品質、データ形式など）
        accuracy = await self._check_translation_accuracy(articles)
        
        # 一貫性チェック
        consistency = self._check_data_consistency(articles)
        
        # 妥当性チェック
        validity = self._check_data_validity(articles)
        
        # 一意性チェック（重複記事）
        uniqueness = self._check_uniqueness(articles)
        
        # 総合品質スコア計算
        overall_score = self._calculate_overall_quality(
            completeness, accuracy, consistency, validity, uniqueness
        )
        
        return QualityMetrics(
            completeness=completeness,
            accuracy=accuracy,
            consistency=consistency,
            validity=validity,
            uniqueness=uniqueness,
            overall_score=overall_score
        )
    
    async def _check_translation_accuracy(self, articles: List[Article]) -> float:
        """翻訳品質チェック"""
        translation_scores = []
        
        for article in articles:
            if not article.translated_title:
                continue
                
            # 基本的な翻訳品質チェック
            score = 1.0
            
            # 文字化けチェック
            if '�' in article.translated_title:
                score -= 0.3
            
            # 長さの妥当性チェック
            if len(article.translated_title) < 5:
                score -= 0.2
            
            # 日本語文字の存在確認
            if not any('\u3040' <= char <= '\u309F' or '\u30A0' <= char <= '\u30FF' or '\u4E00' <= char <= '\u9FAF' for char in article.translated_title):
                score -= 0.4
            
            translation_scores.append(max(score, 0))
        
        return sum(translation_scores) / len(translation_scores) if translation_scores else 0
    
    def _check_data_consistency(self, articles: List[Article]) -> float:
        """データ一貫性チェック"""
        consistency_issues = 0
        total_checks = 0
        
        for article in articles:
            # カテゴリの一貫性
            total_checks += 1
            if article.category not in ['domestic_social', 'international_social', 'tech', 'security', 'economy']:
                consistency_issues += 1
            
            # 重要度スコアの一貫性
            total_checks += 1
            if not (1 <= article.importance_score <= 10):
                consistency_issues += 1
            
            # 日付の一貫性
            total_checks += 1
            if article.published_at and article.collected_at:
                if article.published_at > article.collected_at:
                    consistency_issues += 1
        
        return 1 - (consistency_issues / total_checks) if total_checks > 0 else 1
```

### コード品質監視
```python
import ast
import subprocess
from pathlib import Path

class CodeQualityChecker:
    def __init__(self):
        self.quality_tools = {
            'flake8': self._run_flake8,
            'pylint': self._run_pylint,
            'mypy': self._run_mypy,
            'bandit': self._run_bandit
        }
        
    async def check_code_quality(self, source_dir: str) -> Dict[str, Dict]:
        """コード品質チェック実行"""
        results = {}
        
        for tool_name, tool_func in self.quality_tools.items():
            try:
                results[tool_name] = await tool_func(source_dir)
            except Exception as e:
                results[tool_name] = {'error': str(e), 'score': 0}
        
        return results
    
    async def _run_flake8(self, source_dir: str) -> Dict:
        """Flake8によるスタイルチェック"""
        result = subprocess.run(
            ['flake8', source_dir, '--format=json'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return {'score': 100, 'issues': []}
        
        issues = result.stdout.count('\n')
        score = max(100 - issues * 2, 0)
        
        return {
            'score': score,
            'issues': result.stdout.split('\n'),
            'total_issues': issues
        }
    
    def calculate_code_quality_score(self, results: Dict[str, Dict]) -> float:
        """総合コード品質スコア計算"""
        weights = {
            'flake8': 0.3,
            'pylint': 0.3,
            'mypy': 0.2,
            'bandit': 0.2
        }
        
        weighted_score = 0
        for tool, weight in weights.items():
            if tool in results and 'score' in results[tool]:
                weighted_score += results[tool]['score'] * weight
        
        return weighted_score
```

### 配信品質管理
```python
class DeliveryQualityChecker:
    def __init__(self):
        self.quality_criteria = {
            'content_quality': 0.9,
            'delivery_success_rate': 0.98,
            'response_time': 600,  # 10分
            'user_satisfaction': 4.5
        }
        
    async def validate_delivery_quality(self, delivery_data: Dict) -> Dict:
        """配信品質検証"""
        quality_report = {
            'overall_score': 0,
            'criteria_scores': {},
            'recommendations': []
        }
        
        # コンテンツ品質評価
        content_score = await self._evaluate_content_quality(delivery_data['articles'])
        quality_report['criteria_scores']['content_quality'] = content_score
        
        # 配信成功率
        success_rate = delivery_data['successful_deliveries'] / delivery_data['total_deliveries']
        quality_report['criteria_scores']['delivery_success_rate'] = success_rate
        
        # 応答時間
        response_time_score = min(self.quality_criteria['response_time'] / delivery_data['avg_response_time'], 1.0)
        quality_report['criteria_scores']['response_time'] = response_time_score
        
        # 総合スコア計算
        quality_report['overall_score'] = (
            content_score * 0.4 +
            success_rate * 0.3 +
            response_time_score * 0.3
        ) * 100
        
        # 改善提案生成
        quality_report['recommendations'] = self._generate_quality_recommendations(quality_report)
        
        return quality_report
    
    def _generate_quality_recommendations(self, quality_report: Dict) -> List[str]:
        """品質改善提案生成"""
        recommendations = []
        
        if quality_report['criteria_scores']['content_quality'] < 0.85:
            recommendations.append("コンテンツの翻訳品質と要約品質の改善が必要です")
        
        if quality_report['criteria_scores']['delivery_success_rate'] < 0.95:
            recommendations.append("配信システムの信頼性向上が必要です")
        
        if quality_report['criteria_scores']['response_time'] < 0.8:
            recommendations.append("システムのパフォーマンス最適化が必要です")
        
        return recommendations
```

## 使用する技術・ツール
- **コード品質**: flake8, pylint, mypy, bandit
- **テスト**: pytest, coverage
- **監視**: prometheus_client
- **分析**: pandas, numpy
- **レポート**: matplotlib, jinja2
- **CI/CD**: GitHub Actions

## 連携するエージェント
- **NEWS-Tester**: テスト実行連携
- **NEWS-Analyzer**: データ品質分析
- **NEWS-Monitor**: 品質メトリクス監視
- **NEWS-CSVHandler**: データ品質検証
- **NEWS-Security**: セキュリティ品質

## KPI目標
- **データ品質スコア**: 92%以上
- **コード品質スコア**: 90%以上
- **配信品質スコア**: 95%以上
- **品質改善実施率**: 100%
- **品質問題検出率**: 98%以上

## 品質基準定義

### データ品質基準
- 完全性: 95%以上
- 正確性: 90%以上
- 一貫性: 92%以上
- 妥当性: 88%以上
- 一意性: 98%以上

### コード品質基準
- Flake8: 0エラー
- Pylint: 8.0以上
- テストカバレッジ: 90%以上
- セキュリティスキャン: クリティカル0

### 配信品質基準
- 配信成功率: 98%以上
- レスポンス時間: 10分以内
- コンテンツ品質: 4.5/5以上
- ユーザー満足度: 4.5/5以上

## 自動化機能
- 品質チェック自動実行
- 品質レポート自動生成
- 改善提案自動作成
- アラート自動送信

## 成果物
- 品質管理システム
- 品質メトリクスダッシュボード
- 品質改善レポート
- 品質基準ドキュメント
- 品質監視アラート