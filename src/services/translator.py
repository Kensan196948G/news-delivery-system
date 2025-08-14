"""
Translation Service using DeepL API
DeepL APIを使用した翻訳サービス
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import aiohttp
import deepl
from typing import List, Dict, Any, Optional
import time
import json
from datetime import datetime

from utils.config import get_config
from utils.logger import setup_logger, get_performance_logger
from models.database import Database


class TranslationCache:
    """翻訳結果のキャッシュ管理"""
    
    def __init__(self, config):
        self.config = config
        self.cache_dir = config.get_storage_path('cache')
        self.cache_file = self.cache_dir / 'translation_cache.json'
        self.cache = self._load_cache()
        self.max_cache_size = 10000  # Maximum cached translations
    
    def _load_cache(self) -> Dict[str, Dict]:
        """キャッシュファイルを読み込み"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def _save_cache(self):
        """キャッシュファイルに保存"""
        try:
            # Limit cache size
            if len(self.cache) > self.max_cache_size:
                # Keep only the most recent translations
                sorted_items = sorted(
                    self.cache.items(),
                    key=lambda x: x[1].get('timestamp', ''),
                    reverse=True
                )
                self.cache = dict(sorted_items[:self.max_cache_size])
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def _generate_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """キャッシュキーを生成"""
        import hashlib
        content = f"{text}|{source_lang}|{target_lang}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """キャッシュから翻訳結果を取得"""
        key = self._generate_key(text, source_lang, target_lang)
        cached = self.cache.get(key)
        if cached:
            # Check if cache is still valid (24 hours)
            cache_time = datetime.fromisoformat(cached.get('timestamp', ''))
            if (datetime.now() - cache_time).total_seconds() < 24 * 3600:
                return cached.get('translation')
        return None
    
    def set(self, text: str, source_lang: str, target_lang: str, translation: str):
        """翻訳結果をキャッシュに保存"""
        key = self._generate_key(text, source_lang, target_lang)
        self.cache[key] = {
            'translation': translation,
            'timestamp': datetime.now().isoformat(),
            'source_lang': source_lang,
            'target_lang': target_lang
        }
        self._save_cache()


class DeepLTranslator:
    """DeepL API翻訳サービス"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.api_key = config.get_api_key('deepl')
        self.translator = deepl.Translator(self.api_key)
        self.cache = TranslationCache(config)
        
        # Usage tracking
        self.character_count = 0
        self.monthly_limit = config.get('translation', 'deepl', 'monthly_character_limit', default=500000)
        
        # Language settings
        self.source_languages = config.get('translation', 'deepl', 'source_languages', default=['en'])
        self.target_language = config.get('translation', 'deepl', 'target_language', default='ja')
        self.formality = config.get('translation', 'deepl', 'formality', default='default')
    
    async def translate_text(self, text: str, 
                           source_lang: str = None, 
                           target_lang: str = None,
                           use_cache: bool = True) -> Dict[str, Any]:
        """テキストを翻訳"""
        if not text or len(text.strip()) < 3:
            return {
                'original': text,
                'translated': text,
                'detected_language': 'unknown',
                'characters_used': 0,
                'from_cache': False
            }
        
        source_lang = source_lang or 'auto'
        target_lang = target_lang or self.target_language
        
        # Check cache first
        if use_cache:
            cached_translation = self.cache.get(text, source_lang, target_lang)
            if cached_translation:
                return {
                    'original': text,
                    'translated': cached_translation,
                    'detected_language': source_lang,
                    'characters_used': 0,
                    'from_cache': True
                }
        
        try:
            # Check character limit
            if self.character_count + len(text) > self.monthly_limit:
                self.logger.warning("DeepL monthly character limit reached")
                return {
                    'original': text,
                    'translated': text,  # Return original if limit reached
                    'detected_language': 'unknown',
                    'characters_used': 0,
                    'from_cache': False,
                    'error': 'Monthly limit reached'
                }
            
            start_time = time.time()
            
            # Perform translation
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._translate_sync,
                text,
                source_lang,
                target_lang
            )
            
            response_time = (time.time() - start_time) * 1000
            characters_used = len(text)
            self.character_count += characters_used
            
            # Cache the result
            if use_cache and result['translated']:
                self.cache.set(text, result['detected_language'], target_lang, result['translated'])
            
            # Log API usage
            db = Database(self.config)
            db.log_api_usage(
                'deepl', 'translate', 200, response_time,
                characters_used=characters_used
            )
            
            self.logger.debug(f"DeepL translation: {len(text)} chars -> {len(result['translated'])} chars")
            
            return {
                **result,
                'characters_used': characters_used,
                'from_cache': False
            }
            
        except Exception as e:
            self.logger.error(f"DeepL translation error: {e}")
            return {
                'original': text,
                'translated': text,  # Return original on error
                'detected_language': 'unknown',
                'characters_used': 0,
                'from_cache': False,
                'error': str(e)
            }
    
    def _translate_sync(self, text: str, source_lang: str, target_lang: str) -> Dict[str, str]:
        """同期的翻訳実行（エグゼキュータで使用）"""
        try:
            # Auto-detect source language if not specified
            if source_lang == 'auto' or not source_lang:
                source_lang = None
            
            # Set formality if supported
            kwargs = {}
            if target_lang.upper() in ['DE', 'FR', 'IT', 'ES', 'NL', 'PL', 'PT-PT', 'PT-BR', 'RU']:
                kwargs['formality'] = self.formality
            
            result = self.translator.translate_text(
                text,
                source_lang=source_lang,
                target_lang=target_lang.upper(),
                **kwargs
            )
            
            return {
                'original': text,
                'translated': result.text,
                'detected_language': result.detected_source_lang.lower() if result.detected_source_lang else 'unknown'
            }
            
        except Exception as e:
            raise e
    
    async def translate_batch(self, texts: List[str], 
                            source_lang: str = None, 
                            target_lang: str = None,
                            use_cache: bool = True) -> List[Dict[str, Any]]:
        """バッチ翻訳"""
        if not texts:
            return []
        
        tasks = []
        for text in texts:
            task = self.translate_text(text, source_lang, target_lang, use_cache)
            tasks.append(task)
        
        # Limit concurrent translations to avoid rate limiting
        semaphore = asyncio.Semaphore(5)
        
        async def translate_with_semaphore(text_task):
            async with semaphore:
                return await text_task
        
        results = await asyncio.gather(
            *[translate_with_semaphore(task) for task in tasks],
            return_exceptions=True
        )
        
        # Filter out exceptions
        valid_results = []
        for result in results:
            if isinstance(result, dict):
                valid_results.append(result)
            else:
                # Handle exceptions
                valid_results.append({
                    'original': '',
                    'translated': '',
                    'detected_language': 'unknown',
                    'characters_used': 0,
                    'from_cache': False,
                    'error': str(result)
                })
        
        return valid_results
    
    def get_usage_info(self) -> Dict[str, Any]:
        """使用量情報を取得"""
        try:
            usage = self.translator.get_usage()
            return {
                'character_count': usage.character.count,
                'character_limit': usage.character.limit,
                'character_remaining': usage.character.limit - usage.character.count if usage.character.limit else None,
                'usage_percentage': (usage.character.count / usage.character.limit * 100) if usage.character.limit else 0
            }
        except Exception as e:
            self.logger.error(f"Failed to get DeepL usage info: {e}")
            return {
                'character_count': self.character_count,
                'character_limit': self.monthly_limit,
                'character_remaining': self.monthly_limit - self.character_count,
                'usage_percentage': (self.character_count / self.monthly_limit * 100)
            }


class TranslatorService:
    """統合翻訳サービス"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = setup_logger(__name__)
        self.performance_logger = get_performance_logger(__name__)
        
        # Initialize translators
        self.deepl = DeepLTranslator(self.config, self.logger) if self.config.is_service_enabled('deepl') else None
        
        # Supported languages for translation
        self.translate_from_languages = self.config.get('translation', 'deepl', 'source_languages', default=['en'])
    
    async def translate_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """記事リストを翻訳"""
        if not self.deepl:
            self.logger.warning("DeepL translator not available")
            return articles
        
        self.performance_logger.start_timer("translate_articles")
        
        try:
            translated_articles = []
            
            for article in articles:
                translated_article = await self.translate_single_article(article)
                translated_articles.append(translated_article)
            
            self.logger.info(f"Translated {len(translated_articles)} articles")
            
        except Exception as e:
            self.logger.error(f"Error translating articles: {e}")
            translated_articles = articles  # Return original on error
        
        finally:
            self.performance_logger.end_timer("translate_articles")
        
        return translated_articles
    
    async def translate_single_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """単一記事を翻訳"""
        if not self.deepl:
            return article
        
        language = article.get('language', 'unknown').lower()
        
        # Skip if already in Japanese or unsupported language
        if language == 'ja' or language not in self.translate_from_languages:
            return article
        
        try:
            # Translate title
            title_result = await self.deepl.translate_text(
                article.get('title', ''),
                source_lang=language,
                target_lang='ja'
            )
            
            # Translate content
            content_result = await self.deepl.translate_text(
                article.get('content', ''),
                source_lang=language,
                target_lang='ja'
            )
            
            # Update article with translations
            translated_article = article.copy()
            translated_article.update({
                'title_translated': title_result['translated'],
                'content_translated': content_result['translated'],
                'detected_language': title_result['detected_language'],
                'translation_info': {
                    'title_characters': title_result['characters_used'],
                    'content_characters': content_result['characters_used'],
                    'total_characters': title_result['characters_used'] + content_result['characters_used'],
                    'from_cache': title_result['from_cache'] and content_result['from_cache']
                }
            })
            
            return translated_article
            
        except Exception as e:
            self.logger.error(f"Error translating single article: {e}")
            return article
    
    async def translate_summary_texts(self, texts: List[str], 
                                    source_lang: str = 'en',
                                    target_lang: str = 'ja') -> List[str]:
        """要約テキストのバッチ翻訳"""
        if not self.deepl or not texts:
            return texts
        
        try:
            results = await self.deepl.translate_batch(texts, source_lang, target_lang)
            return [result['translated'] for result in results]
            
        except Exception as e:
            self.logger.error(f"Error translating summaries: {e}")
            return texts
    
    def needs_translation(self, article: Dict[str, Any]) -> bool:
        """記事が翻訳を必要とするかチェック"""
        language = article.get('language', 'unknown').lower()
        
        # Check if already translated
        if article.get('title_translated') or article.get('content_translated'):
            return False
        
        # Check if translation is needed
        return language in self.translate_from_languages and language != 'ja'
    
    def get_translation_stats(self) -> Dict[str, Any]:
        """翻訳統計を取得"""
        stats = {
            'deepl_available': self.deepl is not None,
            'supported_languages': self.translate_from_languages,
        }
        
        if self.deepl:
            usage_info = self.deepl.get_usage_info()
            stats.update(usage_info)
        
        return stats
    
    async def test_translation(self) -> Dict[str, Any]:
        """翻訳サービスのテスト"""
        if not self.deepl:
            return {'status': 'error', 'message': 'DeepL service not available'}
        
        try:
            test_text = "This is a test translation."
            result = await self.deepl.translate_text(test_text, 'en', 'ja')
            
            return {
                'status': 'success',
                'test_input': test_text,
                'test_output': result['translated'],
                'detected_language': result['detected_language'],
                'characters_used': result['characters_used']
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }