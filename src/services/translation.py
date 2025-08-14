"""
Enhanced Translation Service using DeepL API
翻訳サービス強化版 - 非同期バッチ処理対応
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional, Tuple
import time
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

import deepl

from utils.config import get_config
from utils.rate_limiter import RateLimiter
from utils.cache_manager import CacheManager
from models.article import Article


logger = logging.getLogger(__name__)


class TranslationPriority(Enum):
    """翻訳優先度"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class TranslationJobResult:
    """翻訳ジョブ結果"""
    total_articles: int
    translated_articles: int
    skipped_articles: int
    failed_articles: int
    total_characters: int
    processing_time: float
    cache_hit_rate: float
    errors: List[str]


class TranslationError(Exception):
    """Translation specific error"""
    pass


class TranslationService:
    """Enhanced Translation service using DeepL API with batch processing"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.rate_limiter = RateLimiter()
        self.cache_manager = CacheManager()
        
        # Initialize DeepL client
        api_key = self.config.get_api_key('deepl')
        if not api_key:
            logger.warning("DeepL API key not provided")
            self.translator = None
        else:
            self.translator = deepl.Translator(api_key)
        
        # Configuration
        self.target_language = self.config.get('translation.deepl.target_language', 'JA')
        self.formality = self.config.get('translation.deepl.formality', 'default')
        self.max_chars_per_request = 5000
        self.batch_size = self.config.get('translation.batch_size', default=20)
        self.max_concurrent = self.config.get('translation.max_concurrent', default=3)
        self.max_retries = self.config.get('translation.max_retries', default=3)
        self.cache_ttl = self.config.get('translation.cache_ttl', default=86400 * 7)  # 7日間
        
        # Character usage tracking
        self.characters_used = 0
        self.monthly_limit = self.config.get('translation.deepl.rate_limit', 500000)
        
        # 統計情報
        self.translation_stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'errors': 0,
            'total_processing_time': 0.0
        }
        
        logger.info("Enhanced Translation Service initialized")
    
    async def translate_articles(self, articles: List[Article]) -> List[Article]:
        """Translate multiple articles"""
        translated_articles = []
        
        for article in articles:
            try:
                # Skip if already translated or is Japanese
                if (article.title_translated and article.content_translated) or \
                   article.language.value == 'ja':
                    translated_articles.append(article)
                    continue
                
                # Check rate limits
                await self.rate_limiter.wait_if_needed('deepl')
                
                # Translate the article
                translated_article = await self._translate_article(article)
                translated_articles.append(translated_article)
                
                # Record API usage
                self.rate_limiter.record_request('deepl')
                
                # Small delay between requests
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to translate article '{article.title}': {e}")
                # Add original article even if translation failed
                translated_articles.append(article)
        
        logger.info(f"Translated {len([a for a in translated_articles if a.title_translated])} "
                   f"out of {len(articles)} articles")
        
        return translated_articles
    
    async def _translate_article(self, article: Article) -> Article:
        """Translate a single article"""
        try:
            # Prepare text for translation
            title_text = article.title
            content_text = article.content[:2000]  # Limit content length
            
            # Calculate character count
            total_chars = len(title_text) + len(content_text)
            
            # Check if we would exceed monthly limit
            if self.characters_used + total_chars > self.monthly_limit:
                logger.warning("Monthly character limit would be exceeded, skipping translation")
                return article
            
            # Translate title and content
            translated_title = await self._translate_text(title_text)
            translated_content = await self._translate_text(content_text) if content_text else ""
            
            # Update character usage
            self.characters_used += total_chars
            
            # Create updated article
            article.title_translated = translated_title
            article.content_translated = translated_content
            
            logger.debug(f"Translated article: {article.title[:50]}...")
            
            return article
            
        except Exception as e:
            logger.error(f"Translation failed for article: {e}")
            return article
    
    async def _translate_text(self, text: str) -> str:
        """Translate a single text string"""
        if not text or not text.strip():
            return text
        
        try:
            # Use synchronous DeepL API in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._sync_translate, 
                text
            )
            
            return result.text if result else text
            
        except Exception as e:
            logger.error(f"DeepL translation error: {e}")
            return text
    
    def _sync_translate(self, text: str) -> deepl.TextResult:
        """Synchronous translation using DeepL library"""
        return self.translator.translate_text(
            text,
            target_lang=self.target_language,
            formality=self.formality if self.formality != 'default' else None
        )
    
    async def translate_vulnerability_info(self, vulnerability: Dict[str, Any]) -> Dict[str, Any]:
        """Translate vulnerability information"""
        try:
            # Check rate limits
            await self.rate_limiter.wait_if_needed('deepl')
            
            # Translate title and description
            if vulnerability.get('title'):
                vulnerability['title_translated'] = await self._translate_text(
                    vulnerability['title']
                )
            
            if vulnerability.get('description'):
                # Limit description length
                desc = vulnerability['description'][:1500]
                vulnerability['description_translated'] = await self._translate_text(desc)
            
            self.rate_limiter.record_request('deepl')
            
            return vulnerability
            
        except Exception as e:
            logger.error(f"Failed to translate vulnerability: {e}")
            return vulnerability
    
    def get_usage_info(self) -> Dict[str, Any]:
        """Get translation usage information"""
        try:
            usage = self.translator.get_usage()
            
            return {
                'characters_used': self.characters_used,
                'monthly_limit': self.monthly_limit,
                'remaining_characters': self.monthly_limit - self.characters_used,
                'usage_percentage': (self.characters_used / self.monthly_limit) * 100,
                'deepl_usage': {
                    'character_count': usage.character.count,
                    'character_limit': usage.character.limit if usage.character.limit else 'unlimited'
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get usage info: {e}")
            return {
                'characters_used': self.characters_used,
                'monthly_limit': self.monthly_limit,
                'error': str(e)
            }
    
    def check_translation_needed(self, articles: List[Article]) -> List[Article]:
        """Filter articles that need translation"""
        needs_translation = []
        
        for article in articles:
            # Skip if already translated
            if article.title_translated and article.content_translated:
                continue
            
            # Skip Japanese articles
            if article.language.value == 'ja':
                continue
            
            # Skip if content is too short
            if len(article.title) < 5 and len(article.content) < 20:
                continue
            
            needs_translation.append(article)
        
        logger.info(f"Found {len(needs_translation)} articles that need translation")
        return needs_translation
    
    async def batch_translate(self, texts: List[str], max_batch_size: int = 50) -> List[str]:
        """Translate multiple texts in batches"""
        if not texts:
            return []
        
        results = []
        
        # Process in batches
        for i in range(0, len(texts), max_batch_size):
            batch = texts[i:i + max_batch_size]
            
            # Check rate limits
            await self.rate_limiter.wait_if_needed('deepl')
            
            try:
                # Translate batch
                batch_results = []
                for text in batch:
                    translated = await self._translate_text(text)
                    batch_results.append(translated)
                
                results.extend(batch_results)
                
                # Record API usage
                self.rate_limiter.record_request('deepl')
                
                # Delay between batches
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Batch translation failed: {e}")
                # Add original texts if translation fails
                results.extend(batch)
        
        return results
    
    def is_translation_enabled(self) -> bool:
        """Check if translation service is enabled and configured"""
        return (
            self.config.get('translation.deepl.enabled', True) and
            self.config.get_api_key('deepl') is not None
        )
    
    def estimate_cost(self, articles: List[Article]) -> Dict[str, Any]:
        """Estimate translation cost for articles"""
        total_chars = 0
        translatable_articles = 0
        
        for article in articles:
            if article.language.value != 'ja' and not article.title_translated:
                char_count = len(article.title) + len(article.content[:2000])
                total_chars += char_count
                translatable_articles += 1
        
        # DeepL pricing (approximate)
        chars_per_euro = 250000  # Free plan limit
        estimated_cost = (total_chars / chars_per_euro) if total_chars > chars_per_euro else 0
        
        return {
            'total_characters': total_chars,
            'translatable_articles': translatable_articles,
            'estimated_cost_eur': estimated_cost,
            'within_free_limit': total_chars <= chars_per_euro,
            'remaining_free_chars': max(0, chars_per_euro - self.characters_used)
        }