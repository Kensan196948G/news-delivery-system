# NEWS-L10n - 国際化・ローカライゼーションエージェント

## エージェント概要
ニュース配信システムの国際化（i18n）・ローカライゼーション（L10n）対応を専門とするエージェント。

## 役割と責任
- 多言語対応システム設計
- 地域別コンテンツ最適化
- 文化的適応対応
- 時差・地域設定管理
- 多言語品質保証

## 主要業務

### 多言語対応システム実装
```python
from typing import Dict, List, Any, Optional
import json
import gettext
from babel import Locale, dates, numbers
from babel.messages import Catalog
from datetime import datetime, timezone

class InternationalizationManager:
    def __init__(self):
        self.supported_languages = {
            'ja': {'name': 'Japanese', 'native': '日本語', 'rtl': False},
            'en': {'name': 'English', 'native': 'English', 'rtl': False},
            'ko': {'name': 'Korean', 'native': '한국어', 'rtl': False},
            'zh': {'name': 'Chinese', 'native': '中文', 'rtl': False},
            'ar': {'name': 'Arabic', 'native': 'العربية', 'rtl': True},
            'es': {'name': 'Spanish', 'native': 'Español', 'rtl': False},
            'fr': {'name': 'French', 'native': 'Français', 'rtl': False}
        }
        self.translation_catalogs = {}
        self.locale_data = {}
        
    async def initialize_localization(self, language_codes: List[str]):
        """ローカライゼーション初期化"""
        for lang_code in language_codes:
            # 翻訳カタログ読み込み
            catalog = await self._load_translation_catalog(lang_code)
            self.translation_catalogs[lang_code] = catalog
            
            # ロケール情報設定
            locale_info = await self._setup_locale_info(lang_code)
            self.locale_data[lang_code] = locale_info
    
    async def _load_translation_catalog(self, language_code: str) -> Dict:
        """翻訳カタログ読み込み"""
        try:
            catalog_path = f"locales/{language_code}/LC_MESSAGES/messages.po"
            with open(catalog_path, 'r', encoding='utf-8') as f:
                # POファイル解析（実際の実装ではgettext.GNUTranslationsを使用）
                translations = self._parse_po_file(f.read())
                return translations
        except FileNotFoundError:
            # デフォルト翻訳を返す
            return await self._create_default_translations(language_code)
    
    def translate_text(self, text: str, language_code: str, context: str = None) -> str:
        """テキスト翻訳"""
        catalog = self.translation_catalogs.get(language_code, {})
        
        # コンテキスト付き翻訳キー
        translation_key = f"{context}:{text}" if context else text
        
        # 翻訳取得
        translated = catalog.get(translation_key, catalog.get(text, text))
        
        return translated
    
    def format_datetime(self, dt: datetime, language_code: str, format_type: str = 'medium') -> str:
        """日時の地域化フォーマット"""
        locale = Locale(language_code)
        
        if format_type == 'relative':
            # 相対時間表示（例：2時間前）
            return self._format_relative_time(dt, language_code)
        else:
            # 標準日時フォーマット
            return dates.format_datetime(dt, format=format_type, locale=locale)
    
    def format_number(self, number: float, language_code: str, number_type: str = 'decimal') -> str:
        """数値の地域化フォーマット"""
        locale = Locale(language_code)
        
        if number_type == 'currency':
            # 通貨フォーマット（ニュースの経済情報で使用）
            currency_code = self.locale_data[language_code].get('currency', 'USD')
            return numbers.format_currency(number, currency_code, locale=locale)
        elif number_type == 'percent':
            return numbers.format_percent(number, locale=locale)
        else:
            return numbers.format_decimal(number, locale=locale)
```

### 地域別コンテンツ最適化
```python
class RegionalContentOptimizer:
    def __init__(self):
        self.regional_preferences = RegionalPreferences()
        self.cultural_adapters = CulturalAdapters()
        
    async def optimize_content_for_region(self, content: Dict, region_code: str) -> Dict:
        """地域別コンテンツ最適化"""
        optimized_content = content.copy()
        
        # 地域別ニュースカテゴリ優先度調整
        category_priorities = await self._get_regional_category_priorities(region_code)
        optimized_content['category_priorities'] = category_priorities
        
        # 文化的配慮による内容調整
        cultural_adjustments = await self._apply_cultural_adjustments(content, region_code)
        optimized_content.update(cultural_adjustments)
        
        # 地域固有の表記法適用
        notation_adjustments = await self._apply_regional_notation(content, region_code)
        optimized_content.update(notation_adjustments)
        
        # 時差調整
        time_adjustments = await self._apply_timezone_adjustments(content, region_code)
        optimized_content.update(time_adjustments)
        
        return optimized_content
    
    async def _get_regional_category_priorities(self, region_code: str) -> Dict[str, int]:
        """地域別カテゴリ優先度取得"""
        regional_priorities = {
            'JP': {  # 日本
                'domestic_social': 10,
                'international_social': 7,
                'tech': 9,
                'security': 8,
                'economy': 8,
                'disaster_prevention': 10  # 日本特有
            },
            'US': {  # アメリカ
                'domestic_social': 9,
                'international_social': 6,
                'tech': 10,
                'security': 9,
                'economy': 9,
                'politics': 8
            },
            'KR': {  # 韓国
                'domestic_social': 9,
                'international_social': 8,
                'tech': 10,
                'security': 9,
                'economy': 7,
                'k_culture': 8  # 韓流・K-カルチャー
            }
        }
        
        return regional_priorities.get(region_code, {})
    
    async def _apply_cultural_adjustments(self, content: Dict, region_code: str) -> Dict:
        """文化的配慮による調整"""
        adjustments = {}
        
        # 宗教的配慮
        if region_code in ['SA', 'AE', 'EG']:  # 中東地域
            # イスラム教の祝日や慣習に配慮
            adjustments['prayer_time_awareness'] = True
            adjustments['halal_content_filter'] = True
            
        # 政治的配慮
        if region_code == 'CN':  # 中国
            # 特定の政治的話題への配慮
            adjustments['political_sensitivity_filter'] = True
            
        # 言語的配慮
        if region_code in ['AR', 'FA', 'HE']:  # 右から左に読む言語
            adjustments['text_direction'] = 'rtl'
            adjustments['layout_mirror'] = True
            
        return adjustments
    
    def create_multilingual_email_template(self, base_template: str, language_code: str) -> str:
        """多言語メールテンプレート作成"""
        template_adjustments = {
            'ja': {
                'font_family': '"Noto Sans JP", "Hiragino Sans", "Yu Gothic", sans-serif',
                'line_height': '1.8',
                'text_align': 'left',
                'font_size_adjustment': '+2px'
            },
            'ko': {
                'font_family': '"Noto Sans KR", "Malgun Gothic", sans-serif',
                'line_height': '1.7',
                'text_align': 'left'
            },
            'zh': {
                'font_family': '"Noto Sans SC", "Microsoft YaHei", sans-serif',
                'line_height': '1.7',
                'text_align': 'left'
            },
            'ar': {
                'font_family': '"Noto Sans Arabic", "Tahoma", sans-serif',
                'line_height': '1.8',
                'text_align': 'right',
                'direction': 'rtl'
            },
            'en': {
                'font_family': '"Helvetica Neue", Arial, sans-serif',
                'line_height': '1.6',
                'text_align': 'left'
            }
        }
        
        style_adjustments = template_adjustments.get(language_code, template_adjustments['en'])
        
        # CSS スタイル調整を適用
        adjusted_template = self._apply_font_and_layout_adjustments(base_template, style_adjustments)
        
        return adjusted_template
```

### 翻訳品質管理
```python
class TranslationQualityManager:
    def __init__(self):
        self.quality_checkers = QualityCheckers()
        self.terminology_manager = TerminologyManager()
        
    async def validate_translation_quality(self, original_text: str, translated_text: str, 
                                         source_lang: str, target_lang: str) -> Dict:
        """翻訳品質検証"""
        quality_report = {}
        
        # 基本品質チェック
        basic_checks = await self._run_basic_quality_checks(translated_text, target_lang)
        quality_report['basic_quality'] = basic_checks
        
        # 文体一貫性チェック
        style_consistency = await self._check_style_consistency(translated_text, target_lang)
        quality_report['style_consistency'] = style_consistency
        
        # 用語統一チェック
        terminology_consistency = await self._check_terminology_consistency(
            original_text, translated_text, source_lang, target_lang
        )
        quality_report['terminology'] = terminology_consistency
        
        # 文化的適切性チェック
        cultural_appropriateness = await self._check_cultural_appropriateness(
            translated_text, target_lang
        )
        quality_report['cultural_appropriateness'] = cultural_appropriateness
        
        # 総合品質スコア計算
        overall_score = self._calculate_translation_quality_score(quality_report)
        quality_report['overall_score'] = overall_score
        
        return quality_report
    
    async def _run_basic_quality_checks(self, text: str, language_code: str) -> Dict:
        """基本品質チェック"""
        checks = {
            'has_content': len(text.strip()) > 0,
            'appropriate_length': 10 <= len(text) <= 10000,
            'no_encoding_issues': '�' not in text,
            'proper_punctuation': self._check_punctuation(text, language_code),
            'no_machine_translation_artifacts': self._detect_mt_artifacts(text)
        }
        
        return {
            'passed_checks': sum(checks.values()),
            'total_checks': len(checks),
            'details': checks
        }
    
    def _detect_mt_artifacts(self, text: str) -> bool:
        """機械翻訳の特徴検出"""
        mt_artifacts = [
            'DeepL',  # 翻訳サービス名が残っている
            '[翻訳元:',  # 翻訳ツールのマーキング
            '※この翻訳は',  # 自動生成メッセージ
            'Translated by',
            'Machine translated'
        ]
        
        return not any(artifact in text for artifact in mt_artifacts)
    
    def create_translation_memory(self, translation_pairs: List[Dict]) -> Dict:
        """翻訳メモリ作成"""
        tm_database = {}
        
        for pair in translation_pairs:
            source_text = pair['source']
            target_text = pair['target']
            source_lang = pair['source_lang']
            target_lang = pair['target_lang']
            
            # 翻訳ペアをインデックス化
            tm_key = f"{source_lang}-{target_lang}:{hash(source_text)}"
            tm_database[tm_key] = {
                'source': source_text,
                'target': target_text,
                'quality_score': pair.get('quality_score', 0.8),
                'usage_count': 0,
                'last_used': datetime.now(),
                'context': pair.get('context', ''),
                'domain': pair.get('domain', 'news')
            }
        
        return tm_database
    
    def suggest_translation_improvements(self, translation_quality_report: Dict) -> List[str]:
        """翻訳改善提案"""
        suggestions = []
        
        if translation_quality_report['basic_quality']['passed_checks'] < 4:
            suggestions.append("基本的な翻訳品質を向上させる必要があります")
        
        if translation_quality_report['style_consistency']['score'] < 0.7:
            suggestions.append("文体の一貫性を改善してください")
        
        if translation_quality_report['terminology']['consistency_rate'] < 0.8:
            suggestions.append("専門用語の統一性を向上させてください")
        
        if translation_quality_report['cultural_appropriateness']['score'] < 0.8:
            suggestions.append("文化的な適切性を考慮した表現に調整してください")
        
        return suggestions
```

## 使用する技術・ツール
- **国際化**: Babel, gettext
- **翻訳**: DeepL API, Google Translate API
- **フォント**: Noto Fonts, Google Fonts
- **ロケール**: CLDR, ICU
- **文字エンコーディング**: UTF-8, Unicode
- **品質管理**: 翻訳メモリ、用語集

## 連携するエージェント
- **NEWS-Analyzer**: 多言語AI分析
- **NEWS-DevUI**: 多言語UI実装
- **NEWS-Accessibility**: 多言語アクセシビリティ
- **NEWS-UX**: 多言語UX設計
- **NEWS-ReportGen**: 多言語レポート生成

## KPI目標
- **対応言語数**: 7言語以上
- **翻訳品質スコア**: 85%以上
- **地域化完成率**: 90%以上
- **多言語配信成功率**: 98%以上
- **文化的適切性**: 90%以上

## 国際化対応領域

### 言語対応
- テキスト翻訳
- UI要素翻訳
- エラーメッセージ翻訳
- ヘルプドキュメント翻訳

### 地域化対応
- 日時形式
- 数値表記
- 通貨表示
- 住所形式

### 文化的対応
- 色彩の文化的意味
- 画像・アイコンの適切性
- 宗教的配慮
- 政治的配慮

### 技術的対応
- 文字エンコーディング
- フォント選択
- テキスト方向（LTR/RTL）
- 入力メソッド

## 品質保証
- 翻訳品質チェック
- 文化的適切性検証
- ネイティブレビュー
- ユーザビリティテスト

## 継続的改善
- 翻訳メモリ蓄積
- 用語集管理
- 品質フィードバック収集
- 地域別パフォーマンス分析

## 成果物
- 多言語対応システム
- 翻訳品質管理ツール
- 地域別コンテンツ最適化
- 文化的ガイドライン
- 国際化テストスイート