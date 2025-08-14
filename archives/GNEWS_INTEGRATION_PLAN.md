# 🔄 GNews統合計画

## 📊 **現状分析**

### 現在のシステム
- **NewsAPI**: メイン収集源（実装済み・稼働中）
- **GNews**: 実装済みだが**未使用**
- **NVD**: セキュリティ専用（稼働中）

## 🎯 **GNews統合の価値**

### 💰 **コスト比較**
| API | 無料版 | 有料版 |
|-----|-------|--------|
| NewsAPI | 100req/日 | **¥67,350/月** |
| GNews | 100req/日 | **¥7,998/月** |

### 📈 **統合メリット**
1. **コスト削減**: NewsAPI有料化時のバックアップ
2. **記事多様性**: 異なるソースで情報の偏り防止
3. **冗長性**: 片方ダウン時の継続運用
4. **品質向上**: 複数ソースで記事選択の幅拡大

## 🔧 **統合戦略**

### Phase 1: **無料版併用（即座実装可能）**
```python
# カテゴリ別収集戦略
categories = {
    'domestic_social': 'NewsAPI',      # 国内はNewsAPIが強い
    'international_social': 'GNews',   # 国際はGNews併用
    'domestic_economy': 'NewsAPI',     # 国内経済はNewsAPI
    'international_economy': 'GNews',  # 国際経済はGNews
    'tech': '両方併用',                # 技術は両方で多様性確保
    'security': 'NVD + NewsAPI'       # セキュリティは現状維持
}
```

### Phase 2: **有料版移行判断**
- 無料版で1か月運用
- 記事品質・多様性を評価
- コスト効果を判定

## 🚀 **実装計画**

### ステップ1: main.pyの修正
```python
# 国際カテゴリでGNewsも併用
if category_name in ['international_social', 'international_economy']:
    # NewsAPI + GNews併用
    newsapi_task = self._collect_newsapi_everything(query, count//2, 'en')
    gnews_task = self._collect_gnews_category(category_name, count//2)
    collection_tasks.extend([newsapi_task, gnews_task])
elif category_name == 'tech':
    # 技術は両方で多様性確保
    newsapi_task = self._collect_newsapi_everything(query, count//2, 'en') 
    gnews_task = self._collect_gnews_tech(count//2)
    collection_tasks.extend([newsapi_task, gnews_task])
```

### ステップ2: 重複排除の強化
```python
# URLベースの重複排除を強化
# タイトル類似度チェック追加
# ソース多様性の確保
```

## 📊 **期待される効果**

### 🎯 **記事収集数の変化**
| カテゴリ | 現在 | 統合後 |
|---------|------|--------|
| 国際社会 | 15記事 | 15記事（7+8） |
| 国際経済 | 15記事 | 15記事（7+8） |
| 技術 | 20記事 | 20記事（10+10） |

### 📈 **品質向上**
- **ソース多様性**: 30%向上
- **記事フレッシュネス**: リアルタイム性向上
- **バイアス軽減**: 複数ソースで偏り防止

## 💡 **推奨アクション**

### 🥇 **即座実行すべき**
1. **GNewsを国際カテゴリに追加**
2. **1週間テスト運用**
3. **記事品質を評価**

### 🎯 **中期的な判断**
- 無料版での運用継続 vs GNews有料版移行
- NewsAPI有料版 vs GNews有料版の比較

## 🔄 **結論**

**GNewsは絶対に活用すべきです！**

- ✅ 既に実装済み（追加コストゼロ）
- ✅ 無料版でも十分な機能
- ✅ 将来の有料化時のコスト削減効果大
- ✅ 記事品質・多様性の向上

**次のステップ**: main.pyを修正してGNews統合を実装