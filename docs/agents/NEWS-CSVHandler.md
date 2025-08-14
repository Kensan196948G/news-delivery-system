# NEWS-CSVHandler - データ処理・CSV操作エージェント

## エージェント概要
ニュース配信システムのデータ処理、CSV操作、データ変換を専門とするエージェント。

## 役割と責任
- CSV データの読み込み・書き出し
- データクレンジング・変換
- バッチデータ処理
- データエクスポート・インポート
- 統計レポート生成

## 主要業務

### CSV データ処理
```python
import pandas as pd
import numpy as np
from typing import List, Dict, Optional

class NewsCSVHandler:
    def __init__(self):
        self.encoding = 'utf-8-sig'  # BOM付きUTF-8
        self.date_format = '%Y-%m-%d %H:%M:%S'
        
    async def export_articles_to_csv(
        self, 
        articles: List[Article], 
        output_path: str,
        include_analysis: bool = True
    ) -> bool:
        """記事データのCSVエクスポート"""
        try:
            df_data = []
            
            for article in articles:
                row_data = {
                    'id': article.id,
                    'url': article.url,
                    'title': article.title,
                    'translated_title': article.translated_title,
                    'description': article.description,
                    'content': article.content[:500] + '...' if len(article.content) > 500 else article.content,
                    'source_name': article.source_name,
                    'author': article.author,
                    'published_at': article.published_at.strftime(self.date_format) if article.published_at else '',
                    'collected_at': article.collected_at.strftime(self.date_format),
                    'category': article.category,
                    'importance_score': article.importance_score,
                    'keywords': ','.join(article.keywords) if article.keywords else '',
                    'sentiment': article.sentiment,
                    'processed': article.processed
                }
                
                if include_analysis and article.ai_analysis:
                    row_data.update({
                        'ai_summary': article.ai_analysis.summary,
                        'ai_key_points': ','.join(article.ai_analysis.key_points),
                        'impact_analysis': article.ai_analysis.impact_analysis
                    })
                
                df_data.append(row_data)
            
            df = pd.DataFrame(df_data)
            df.to_csv(output_path, index=False, encoding=self.encoding)
            
            return True
            
        except Exception as e:
            self.logger.error(f"CSV export error: {str(e)}")
            return False
```

### データクレンジング
```python
class DataCleaner:
    def clean_article_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """記事データのクレンジング"""
        # 重複除去（URL基準）
        df = df.drop_duplicates(subset=['url'], keep='first')
        
        # 欠損値処理
        df['title'] = df['title'].fillna('')
        df['description'] = df['description'].fillna('')
        df['author'] = df['author'].fillna('Unknown')
        
        # データ型変換
        df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce')
        df['importance_score'] = pd.to_numeric(df['importance_score'], errors='coerce').fillna(5)
        
        # 異常値除去
        df = df[df['importance_score'].between(1, 10)]
        
        # テキスト正規化
        df['title'] = df['title'].str.strip()
        df['category'] = df['category'].str.lower().str.strip()
        
        return df
    
    def validate_data_quality(self, df: pd.DataFrame) -> Dict[str, float]:
        """データ品質指標計算"""
        total_rows = len(df)
        
        quality_metrics = {
            'completeness': {
                'title': (df['title'].notna()).sum() / total_rows,
                'content': (df['content'].notna()).sum() / total_rows,
                'published_at': (df['published_at'].notna()).sum() / total_rows
            },
            'uniqueness': {
                'url_duplicates': df['url'].duplicated().sum(),
                'title_duplicates': df['title'].duplicated().sum()
            },
            'consistency': {
                'category_values': df['category'].nunique(),
                'source_values': df['source_name'].nunique()
            },
            'validity': {
                'valid_importance_scores': df['importance_score'].between(1, 10).sum() / total_rows,
                'valid_dates': df['published_at'].notna().sum() / total_rows
            }
        }
        
        return quality_metrics
```

### 統計レポート生成
```python
class StatisticsGenerator:
    def generate_delivery_stats(self, delivery_df: pd.DataFrame) -> Dict:
        """配信統計レポート生成"""
        stats = {
            'total_deliveries': len(delivery_df),
            'success_rate': (delivery_df['status'] == 'sent').mean() * 100,
            'avg_articles_per_delivery': delivery_df['article_count'].mean(),
            'category_distribution': delivery_df['categories'].value_counts().to_dict(),
            'daily_delivery_trend': delivery_df.groupby(
                delivery_df['delivered_at'].dt.date
            ).size().to_dict(),
            'peak_delivery_hours': delivery_df.groupby(
                delivery_df['delivered_at'].dt.hour
            ).size().sort_values(ascending=False).head(3).to_dict()
        }
        
        return stats
```

### バッチ処理
- 大容量データ分割処理
- メモリ効率的な読み込み
- 並列処理による高速化
- プログレス表示

## 使用する技術・ツール
- **Python**: pandas, numpy
- **データ処理**: dask (大容量データ用)
- **統計**: scipy, matplotlib, seaborn
- **ファイル**: openpyxl (Excel), chardet (エンコーディング検出)
- **並列処理**: multiprocessing
- **メモリ管理**: memory_profiler

## 連携するエージェント
- **NEWS-DataModel**: データモデル定義活用
- **NEWS-ReportGen**: レポート用データ提供
- **NEWS-Monitor**: データ処理監視
- **NEWS-Analyzer**: 分析結果データ処理
- **NEWS-QA**: データ品質検証

## KPI目標
- **処理速度**: 1万件/分以上
- **データ品質**: 完全性95%以上
- **メモリ使用効率**: 2GB以下
- **処理成功率**: 99.5%以上
- **エラー率**: 0.1%未満

## 主要機能

### データ変換
- JSON ⇔ CSV変換
- データフォーマット統一
- エンコーディング変換
- 列名・構造マッピング

### 集計・分析
- カテゴリ別統計
- 時系列分析
- 配信効果分析
- 使用量統計

### データ品質管理
- スキーマ検証
- 異常値検出
- 整合性チェック
- クレンジングルール適用

## エラーハンドリング
- ファイル読み込みエラー対応
- データ型変換エラー処理
- メモリ不足時の分割処理
- 部分的処理継続

## 成果物
- CSV処理スクリプト
- データクレンジング規則
- 統計レポートテンプレート
- データ品質ダッシュボード
- バッチ処理ツール