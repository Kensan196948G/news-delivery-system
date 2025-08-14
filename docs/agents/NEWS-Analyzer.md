# NEWS-Analyzer - AI分析エージェント

## エージェント概要
Claude APIを活用したニュース記事の高度な分析・要約・分類を実行するAI専門エージェント。

## 役割と責任
- AI記事分析実行
- 要約生成・品質管理
- 重要度評価
- センチメント分析
- キーワード抽出・分類

## 主要業務

### Claude API による記事分析
```python
import anthropic
import asyncio
from typing import List, Dict

class ClaudeAnalyzer:
    def __init__(self, api_key: str):
        self.client = anthropic.Client(api_key=api_key)
        
    async def analyze_article(self, article: Article) -> AnalysisResult:
        prompt = self._build_analysis_prompt(article)
        
        response = await asyncio.to_thread(
            self.client.messages.create,
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self._parse_analysis_response(response)
    
    def _build_analysis_prompt(self, article: Article) -> str:
        return f"""
        以下のニュース記事を分析してください。

        タイトル: {article.translated_title or article.title}
        内容: {article.translated_content or article.content}
        カテゴリ: {article.category}
        ソース: {article.source_name}

        以下のJSON形式で詳細な分析結果を提供してください:
        {{
            "summary": "200-250文字の簡潔で的確な要約",
            "importance_score": "1-10の重要度スコア（理由も含む）",
            "keywords": ["関連キーワード5個"],
            "category": "最適なカテゴリ分類",
            "sentiment": "positive/neutral/negative",
            "key_points": ["重要ポイント3つ"],
            "impact_analysis": "影響度分析",
            "urgency_level": "緊急度（1-5）",
            "target_audience": "対象読者層",
            "related_topics": ["関連トピック"]
        }}
        """
```

### バッチ処理・最適化
- 並行分析処理
- API使用量最適化
- キャッシュ活用
- エラー回復処理

### 分析品質管理
```python
class AnalysisQualityController:
    def validate_analysis(self, analysis: AnalysisResult) -> bool:
        """分析結果の品質検証"""
        checks = [
            self._validate_summary_length(analysis.summary),
            self._validate_score_range(analysis.importance_score),
            self._validate_keywords(analysis.keywords),
            self._validate_sentiment(analysis.sentiment)
        ]
        return all(checks)
    
    def _validate_summary_length(self, summary: str) -> bool:
        return 200 <= len(summary) <= 250
    
    def improve_analysis(self, analysis: AnalysisResult) -> AnalysisResult:
        """分析結果の改善・補正"""
        if not self.validate_analysis(analysis):
            return self._reanalyze_with_corrections(analysis)
        return analysis
```

### 専門分野別分析
- セキュリティ脆弱性分析
- 経済指標分析
- 技術トレンド分析
- 社会情勢分析

## 使用する技術・ツール
- **AI API**: Claude API (Anthropic)
- **言語処理**: NLTK, spaCy
- **機械学習**: scikit-learn
- **データ分析**: pandas, numpy
- **並行処理**: asyncio, concurrent.futures
- **キャッシュ**: Redis

## 連携するエージェント
- **NEWS-Logic**: 重要度判定ロジック
- **NEWS-CSVHandler**: 分析結果データ処理
- **NEWS-Monitor**: 分析パフォーマンス監視
- **NEWS-Knowledge**: ナレッジベース活用
- **NEWS-ReportGen**: 分析結果レポート生成

## KPI目標
- **分析精度**: 92%以上
- **処理時間**: 記事あたり3秒以内
- **API使用効率**: 使用量の85%以内
- **要約品質スコア**: 4.5/5以上
- **重要度判定精度**: 88%以上

## 分析カテゴリ別特化

### セキュリティ分析
- CVSS スコア解析
- 影響範囲評価
- 緊急度判定
- 対策優先度

### 経済分析
- 市場影響度評価
- トレンド分析
- 指標重要度
- 投資影響度

### 技術分析
- 技術革新度評価
- 採用可能性分析
- 競争優位性評価
- 標準化動向

## 品質保証機能
- 分析結果検証
- 一貫性チェック
- バイアス検出
- 改善提案生成

## 学習・改善機能
- フィードバック学習
- 分析パターン最適化
- モデル性能向上
- ユーザー満足度向上

## 成果物
- 記事分析結果データ
- 要約・キーワード生成
- 重要度スコア
- 分析品質レポート
- AI使用量統計