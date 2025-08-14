"""
DeepL Translation Module
DeepL翻訳モジュール - バッチ翻訳対応
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import aiohttp
import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from utils.config import get_config
from utils.cache_manager import CacheManager
from utils.rate_limiter import get_rate_limiter
from utils.simple_translator import SimpleTranslator
from models.article import Article, ArticleLanguage


logger = logging.getLogger(__name__)


class TranslationError(Exception):
    """翻訳関連エラー"""
    pass


class TranslationQuality(Enum):
    """翻訳品質設定"""
    NORMAL = "normal"
    HIGH = "more"
    PREFER_QUALITY = "prefer_quality"
    PREFER_SPEED = "prefer_speed"


@dataclass
class TranslationRequest:
    """翻訳リクエスト"""
    text: str
    source_lang: str
    target_lang: str
    formality: str = "default"
    preserve_formatting: bool = True
    split_sentences: str = "1"  # Auto-split sentences


@dataclass
class TranslationResult:
    """翻訳結果"""
    original_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    detected_lang: Optional[str] = None
    confidence: float = 0.0
    character_count: int = 0
    processing_time: float = 0.0
    cache_hit: bool = False


class DeepLTranslator:
    """DeepL翻訳サービス"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.cache_manager = CacheManager()
        self.rate_limiter = get_rate_limiter()
        
        # DeepL API設定
        self.api_key = self.config.get_env('DEEPL_API_KEY')
        # APIキーのフォーマットで無料版か有料版か判定
        if self.api_key and ':fx' in self.api_key:
            # 無料版のAPIキー（末尾に:fxがある）
            self.api_url = "https://api-free.deepl.com/v2/translate"
            self.usage_url = "https://api-free.deepl.com/v2/usage"
        else:
            # 有料版のAPIキー
            self.api_url = "https://api.deepl.com/v2/translate"
            self.usage_url = "https://api.deepl.com/v2/usage"
        
        # 使用量制限設定
        self.monthly_char_limit = self.config.get('translation.monthly_limit', default=500000)
        self.batch_size = self.config.get('translation.batch_size', default=50)
        self.cache_ttl = self.config.get('translation.cache_ttl', default=86400 * 7)  # 7日間
        
        # 翻訳設定
        self.default_quality = TranslationQuality.HIGH
        self.supported_languages = {
            'en': 'EN',  # English
            'ja': 'JA',  # Japanese  
            'de': 'DE',  # German
            'fr': 'FR',  # French
            'es': 'ES',  # Spanish
            'it': 'IT',  # Italian
            'pt': 'PT',  # Portuguese
            'ru': 'RU',  # Russian
            'zh': 'ZH',  # Chinese
            'ko': 'KO',  # Korean
        }
        
        # 統計情報
        self.translation_stats = {
            'total_requests': 0,
            'total_characters': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'errors': 0
        }
        
        if not self.api_key:
            logger.warning("DeepL API key not configured")
        
        logger.info("DeepL Translator initialized")
    
    async def translate_article(self, article: Article) -> Article:
        """単一記事の翻訳"""
        try:
            # 翻訳が必要かチェック
            if not self._needs_translation(article):
                logger.debug(f"Article already in Japanese, skipping translation: {article.url}")
                return article
            
            # 翻訳実行
            translation_tasks = []
            
            # ソース言語を判定（デフォルトは英語）
            source_lang = 'en'
            if hasattr(article, 'language') and article.language and hasattr(article.language, 'value'):
                source_lang = article.language.value
            
            if article.title:
                translation_tasks.append(
                    self._translate_text(article.title, source_lang, 'ja')
                )
            
            if article.description:
                translation_tasks.append(
                    self._translate_text(article.description, source_lang, 'ja')
                )
            
            if article.content:
                translation_tasks.append(
                    self._translate_text(article.content, source_lang, 'ja')
                )
            
            # 並列実行
            results = await asyncio.gather(*translation_tasks, return_exceptions=True)
            
            # 結果を記事に適用
            result_index = 0
            if article.title and result_index < len(results):
                result = results[result_index]
                if isinstance(result, TranslationResult):
                    article.translated_title = result.translated_text
                result_index += 1
            
            if article.description and result_index < len(results):
                result = results[result_index]
                if isinstance(result, TranslationResult):
                    article.translated_description = result.translated_text
                result_index += 1
            
            if article.content and result_index < len(results):
                result = results[result_index]
                if isinstance(result, TranslationResult):
                    article.translated_content = result.translated_text
                result_index += 1
            
            logger.debug(f"Article translation completed: {article.url}")
            return article
            
        except Exception as e:
            logger.error(f"Article translation failed: {e}. Using fallback translator.")
            self.translation_stats['errors'] += 1
            # フォールバック: SimpleTranslatorを使用
            return self._fallback_translation(article)
    
    async def translate_batch(self, articles: List[Article]) -> List[Article]:
        """記事のバッチ翻訳"""
        try:
            logger.info(f"Starting batch translation for {len(articles)} articles")
            
            # 翻訳が必要な記事のみフィルタリング
            articles_to_translate = [a for a in articles if self._needs_translation(a)]
            
            if not articles_to_translate:
                logger.info("No articles need translation")
                return articles
            
            logger.info(f"Translating {len(articles_to_translate)} articles")
            
            # セマフォで同時実行数を制限
            semaphore = asyncio.Semaphore(5)  # 最大5並列
            
            async def translate_with_semaphore(article):
                async with semaphore:
                    return await self.translate_article(article)
            
            # バッチ処理
            translated_articles = []
            for i in range(0, len(articles_to_translate), self.batch_size):
                batch = articles_to_translate[i:i + self.batch_size]
                
                # レート制限チェック（文字数込み）
                batch_characters = sum(len(a.title or '') + len(getattr(a, 'content', '') or '') for a in batch)
                await self.rate_limiter.wait_if_needed('deepl', batch_characters)
                
                # バッチ翻訳実行
                batch_results = await asyncio.gather(
                    *[translate_with_semaphore(article) for article in batch],
                    return_exceptions=True
                )
                
                # 結果をマージ
                for result in batch_results:
                    if isinstance(result, Article):
                        translated_articles.append(result)
                    else:
                        logger.error(f"Translation error in batch: {result}")
                
                # API使用量記録（文字数込み）
                self.rate_limiter.record_request('deepl', batch_characters)
                
                logger.info(f"Completed batch {i//self.batch_size + 1}/{(len(articles_to_translate) + self.batch_size - 1)//self.batch_size}")
            
            # 翻訳されなかった記事も含めて返す
            result_map = {a.url: a for a in translated_articles}
            final_articles = []
            
            for article in articles:
                if article.url in result_map:
                    final_articles.append(result_map[article.url])
                else:
                    final_articles.append(article)
            
            logger.info(f"Batch translation completed: {len(translated_articles)} translated")
            return final_articles
            
        except Exception as e:
            logger.error(f"Batch translation failed: {e}")
            raise TranslationError(f"Batch translation failed: {e}")
    
    async def _translate_text(self, text: str, source_lang: str, target_lang: str,
                            quality: TranslationQuality = None) -> TranslationResult:
        """テキスト翻訳"""
        try:
            start_time = datetime.now()
            
            # キャッシュキー生成
            cache_key = self._generate_cache_key(text, source_lang, target_lang)
            
            # キャッシュチェック
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                logger.debug("Translation cache hit")
                self.translation_stats['cache_hits'] += 1
                return TranslationResult(
                    original_text=text,
                    translated_text=cached_result['translated_text'],
                    source_lang=source_lang,
                    target_lang=target_lang,
                    detected_lang=cached_result.get('detected_lang'),
                    confidence=cached_result.get('confidence', 0.0),
                    character_count=len(text),
                    processing_time=0.0,
                    cache_hit=True
                )
            
            # 言語コード変換
            source_code = self._convert_language_code(source_lang)
            target_code = self._convert_language_code(target_lang)
            
            # 翻訳リクエスト準備
            translation_request = TranslationRequest(
                text=text,
                source_lang=source_code,
                target_lang=target_code,
                formality="default"
            )
            
            # API呼び出し
            result = await self._call_deepl_api(translation_request, quality)
            
            # 結果をキャッシュ
            cache_data = {
                'translated_text': result.translated_text,
                'detected_lang': result.detected_lang,
                'confidence': result.confidence
            }
            self.cache_manager.set(cache_key, cache_data, expire=self.cache_ttl)
            
            # 統計更新
            self.translation_stats['total_requests'] += 1
            self.translation_stats['total_characters'] += len(text)
            self.translation_stats['api_calls'] += 1
            
            processing_time = (datetime.now() - start_time).total_seconds()
            result.processing_time = processing_time
            
            logger.debug(f"Translation completed: {len(text)} chars in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Text translation failed: {e}")
            self.translation_stats['errors'] += 1
            raise TranslationError(f"Translation failed: {e}")
    
    async def _call_deepl_api(self, request: TranslationRequest, 
                            quality: TranslationQuality = None) -> TranslationResult:
        """DeepL API呼び出し"""
        try:
            if not self.api_key:
                raise TranslationError("DeepL API key not configured")
            
            # リクエストパラメータ
            params = {
                'auth_key': self.api_key,
                'text': request.text,
                'source_lang': request.source_lang,
                'target_lang': request.target_lang,
                'formality': request.formality,
                'preserve_formatting': '1' if request.preserve_formatting else '0',
                'split_sentences': request.split_sentences
            }
            
            # 品質設定
            if quality:
                if quality == TranslationQuality.HIGH:
                    params['formality'] = 'more'
                elif quality == TranslationQuality.PREFER_QUALITY:
                    params['formality'] = 'prefer_quality'
            
            # API呼び出し
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, data=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise TranslationError(f"DeepL API error {response.status}: {error_text}")
                    
                    result_data = await response.json()
            
            # レスポンス解析
            if 'translations' not in result_data or not result_data['translations']:
                raise TranslationError("No translations returned from DeepL API")
            
            translation = result_data['translations'][0]
            
            return TranslationResult(
                original_text=request.text,
                translated_text=translation['text'],
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                detected_lang=translation.get('detected_source_language'),
                confidence=1.0,  # DeepL doesn't provide confidence scores
                character_count=len(request.text)
            )
            
        except aiohttp.ClientError as e:
            logger.error(f"Network error calling DeepL API: {e}")
            raise TranslationError(f"Network error calling DeepL API: {e}")
        except Exception as e:
            logger.error(f"DeepL API call failed: {e}")
            raise TranslationError(f"DeepL API call failed: {e}")
    
    def _needs_translation(self, article: Article) -> bool:
        """翻訳が必要かチェック"""
        # languageがNoneの場合は英語として扱う
        if not hasattr(article, 'language') or article.language is None:
            # タイトルや内容から言語を推定（英語と仮定）
            return True
            
        # 既に日本語の場合は翻訳不要
        if article.language == ArticleLanguage.JAPANESE:
            return False
        
        # 既に翻訳済みの場合は翻訳不要
        if hasattr(article, 'translated_title') and article.translated_title:
            return False
        
        # 英語以外で翻訳可能な言語かチェック
        if hasattr(article.language, 'value'):
            if article.language.value not in self.supported_languages:
                logger.warning(f"Unsupported language for translation: {article.language.value}")
                return False
        
        return True
    
    def _convert_language_code(self, lang_code: str) -> str:
        """言語コードをDeepL形式に変換"""
        return self.supported_languages.get(lang_code.lower(), lang_code.upper())
    
    def _generate_cache_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """キャッシュキー生成"""
        key_text = f"{source_lang}:{target_lang}:{text}"
        return f"translation:{hashlib.md5(key_text.encode('utf-8')).hexdigest()}"
    
    async def get_usage_info(self) -> Dict[str, Any]:
        """API使用量情報取得"""
        try:
            if not self.api_key:
                return {'error': 'API key not configured'}
            
            async with aiohttp.ClientSession() as session:
                params = {'auth_key': self.api_key}
                async with session.get(self.usage_url, params=params) as response:
                    if response.status != 200:
                        return {'error': f'API error {response.status}'}
                    
                    usage_data = await response.json()
            
            # 使用量情報と統計を組み合わせ
            return {
                'api_usage': usage_data,
                'character_count': usage_data.get('character_count', 0),
                'character_limit': usage_data.get('character_limit', self.monthly_char_limit),
                'usage_percentage': (usage_data.get('character_count', 0) / 
                                   usage_data.get('character_limit', self.monthly_char_limit)) * 100,
                'local_stats': self.translation_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get usage info: {e}")
            return {'error': str(e), 'local_stats': self.translation_stats}
    
    def get_translation_statistics(self) -> Dict[str, Any]:
        """翻訳統計情報取得"""
        cache_hit_rate = (self.translation_stats['cache_hits'] / 
                         max(self.translation_stats['total_requests'], 1)) * 100
        
        return {
            'total_requests': self.translation_stats['total_requests'],
            'total_characters': self.translation_stats['total_characters'],
            'api_calls': self.translation_stats['api_calls'],
            'cache_hits': self.translation_stats['cache_hits'],
            'cache_hit_rate': round(cache_hit_rate, 2),
            'errors': self.translation_stats['errors'],
            'supported_languages': list(self.supported_languages.keys())
        }
    
    async def test_translation(self, test_text: str = None) -> Dict[str, Any]:
        """翻訳機能テスト"""
        try:
            test_text = test_text or "Hello, this is a test translation."
            
            logger.info("Testing DeepL translation...")
            result = await self._translate_text(test_text, 'en', 'ja')
            
            return {
                'success': True,
                'original_text': result.original_text,
                'translated_text': result.translated_text,
                'processing_time': result.processing_time,
                'character_count': result.character_count,
                'cache_hit': result.cache_hit
            }
            
        except Exception as e:
            logger.error(f"Translation test failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def clear_translation_cache(self, older_than_days: int = 7):
        """翻訳キャッシュクリア"""
        try:
            # キャッシュマネージャーのクリア機能を使用
            cleared_count = self.cache_manager.clear_expired()
            logger.info(f"Cleared {cleared_count} expired translation cache entries")
            return cleared_count
        except Exception as e:
            logger.error(f"Failed to clear translation cache: {e}")
            return 0
    
    def _fallback_translation(self, article: Article) -> Article:
        """SimpleTranslatorを使用したフォールバック翻訳"""
        try:
            logger.info(f"Using fallback translator for article: {article.url}")
            
            # タイトルの翻訳
            if article.title and not getattr(article, 'translated_title', None):
                article.translated_title = SimpleTranslator.translate_text(article.title, max_length=100)
            
            # 説明の翻訳
            if article.description and not getattr(article, 'translated_description', None):
                article.translated_description = SimpleTranslator.translate_text(article.description, max_length=200)
            
            # 内容の翻訳または要約生成
            if article.content and not getattr(article, 'translated_content', None):
                # 長い内容は要約を生成
                article.translated_content = SimpleTranslator.create_summary(
                    article.title or '',
                    article.content,
                    max_length=250
                )
            
            logger.info(f"Fallback translation completed for article: {article.url}")
            return article
            
        except Exception as e:
            logger.error(f"Fallback translation also failed: {e}")
            # 最終的なフォールバック: 元のテキストに説明を追加
            if article.title and not getattr(article, 'translated_title', None):
                article.translated_title = f"【未翻訳】{article.title}"
            if article.description and not getattr(article, 'translated_description', None):
                article.translated_description = f"【未翻訳】{article.description}"
            if article.content and not getattr(article, 'translated_content', None):
                article.translated_content = f"【未翻訳記事】{article.content[:200]}..."
            return article


# グローバル翻訳インスタンス
_translator_instance = None


def get_translator() -> DeepLTranslator:
    """グローバル翻訳インスタンス取得"""
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = DeepLTranslator()
    return _translator_instance