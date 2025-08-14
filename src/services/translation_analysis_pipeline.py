"""
Translation and AI Analysis Pipeline
翻訳・AI分析統合パイプライン
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import time

from .translator import TranslatorService
from .ai_analyzer import ClaudeAnalyzer
from utils.config import get_config
from utils.logger import setup_logger, get_performance_logger
from models.article import Article


logger = logging.getLogger(__name__)


class TranslationAnalysisPipeline:
    """翻訳・AI分析統合パイプライン"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = setup_logger(__name__)
        self.performance_logger = get_performance_logger(__name__)
        
        # Initialize services
        self.translator = TranslatorService(self.config)
        self.analyzer = ClaudeAnalyzer(self.config)
        
        # Pipeline configuration
        self.parallel_processing = self.config.get('pipeline', 'parallel_processing', default=True)
        self.max_concurrent_translations = self.config.get('pipeline', 'max_concurrent_translations', default=5)
        self.max_concurrent_analyses = self.config.get('pipeline', 'max_concurrent_analyses', default=3)
        self.batch_size = self.config.get('pipeline', 'batch_size', default=10)
        
        # Performance tracking
        self.pipeline_stats = {
            'articles_processed': 0,
            'translations_completed': 0,
            'analyses_completed': 0,
            'cache_hits': 0,
            'errors': 0,
            'total_processing_time': 0,
            'average_time_per_article': 0
        }
    
    async def process_articles(self, articles: List[Dict[str, Any]]) -> List[Article]:
        """記事の翻訳・分析パイプライン処理"""
        start_time = time.time()
        self.performance_logger.start_timer("pipeline_processing")
        
        try:
            self.logger.info(f"Starting pipeline processing for {len(articles)} articles")
            
            # Convert to Article objects if needed
            article_objects = self._prepare_articles(articles)
            
            if self.parallel_processing:
                processed_articles = await self._process_parallel(article_objects)
            else:
                processed_articles = await self._process_sequential(article_objects)
            
            # Update statistics
            processing_time = time.time() - start_time
            self.pipeline_stats['total_processing_time'] += processing_time
            self.pipeline_stats['articles_processed'] += len(processed_articles)
            self.pipeline_stats['average_time_per_article'] = (
                self.pipeline_stats['total_processing_time'] / 
                max(self.pipeline_stats['articles_processed'], 1)
            )
            
            self.logger.info(
                f"Pipeline completed: {len(processed_articles)} articles processed in {processing_time:.2f}s"
            )
            
            return processed_articles
            
        except Exception as e:
            self.pipeline_stats['errors'] += 1
            self.logger.error(f"Pipeline processing error: {e}")
            raise
            
        finally:
            self.performance_logger.end_timer("pipeline_processing")
    
    def _prepare_articles(self, articles: List[Dict[str, Any]]) -> List[Article]:
        """記事データをArticleオブジェクトに変換"""
        article_objects = []
        
        for article_data in articles:
            try:
                # Create Article object from dictionary
                article = Article(
                    title=article_data.get('title', ''),
                    content=article_data.get('content', ''),
                    url=article_data.get('url', ''),
                    source=article_data.get('source', {}),
                    published_at=article_data.get('published_at'),
                    category=article_data.get('category', 'general'),
                    language=article_data.get('language', 'unknown')
                )
                
                # Set additional fields if available
                if 'description' in article_data:
                    article.description = article_data['description']
                if 'author' in article_data:
                    article.author = article_data['author']
                
                article_objects.append(article)
                
            except Exception as e:
                self.logger.error(f"Error creating Article object: {e}")
                continue
        
        return article_objects
    
    async def _process_parallel(self, articles: List[Article]) -> List[Article]:
        """並列処理による翻訳・分析"""
        self.logger.info("Using parallel processing mode")
        
        # Process in batches to manage memory and API limits
        processed_articles = []
        
        for i in range(0, len(articles), self.batch_size):
            batch = articles[i:i + self.batch_size]
            batch_results = await self._process_batch_parallel(batch)
            processed_articles.extend(batch_results)
            
            # Small delay between batches
            if i + self.batch_size < len(articles):
                await asyncio.sleep(0.5)
        
        return processed_articles
    
    async def _process_batch_parallel(self, batch: List[Article]) -> List[Article]:
        """バッチ並列処理"""
        # Separate articles that need translation vs analysis only
        needs_translation = [a for a in batch if self.translator.needs_translation(a)]
        translation_only = [a for a in batch if a not in needs_translation]
        
        # Translation phase
        translated_articles = []
        if needs_translation:
            translation_tasks = []
            translation_semaphore = asyncio.Semaphore(self.max_concurrent_translations)
            
            for article in needs_translation:
                task = self._translate_with_semaphore(article, translation_semaphore)
                translation_tasks.append(task)
            
            translation_results = await asyncio.gather(*translation_tasks, return_exceptions=True)
            
            for result in translation_results:
                if isinstance(result, Article):
                    translated_articles.append(result)
                    self.pipeline_stats['translations_completed'] += 1
                else:
                    self.logger.error(f"Translation error: {result}")
        
        # Combine translated and non-translated articles
        all_articles = translated_articles + translation_only
        
        # Analysis phase - analyze all articles
        analyzed_articles = []
        if all_articles:
            analysis_tasks = []
            analysis_semaphore = asyncio.Semaphore(self.max_concurrent_analyses)
            
            for article in all_articles:
                task = self._analyze_with_semaphore(article, analysis_semaphore)
                analysis_tasks.append(task)
            
            analysis_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            for result in analysis_results:
                if isinstance(result, Article):
                    analyzed_articles.append(result)
                    self.pipeline_stats['analyses_completed'] += 1
                else:
                    self.logger.error(f"Analysis error: {result}")
        
        return analyzed_articles
    
    async def _translate_with_semaphore(self, article: Article, semaphore: asyncio.Semaphore) -> Article:
        """セマフォ付き翻訳処理"""
        async with semaphore:
            return await self.translator.translate_single_article(article.__dict__)
    
    async def _analyze_with_semaphore(self, article: Article, semaphore: asyncio.Semaphore) -> Article:
        """セマフォ付き分析処理"""
        async with semaphore:
            return await self.analyzer._analyze_article(article)
    
    async def _process_sequential(self, articles: List[Article]) -> List[Article]:
        """逐次処理による翻訳・分析"""
        self.logger.info("Using sequential processing mode")
        
        processed_articles = []
        
        for article in articles:
            try:
                # Translation phase
                if self.translator.needs_translation(article):
                    translated_data = await self.translator.translate_single_article(article.__dict__)
                    # Update article with translation
                    article.title_translated = translated_data.get('title_translated')
                    article.content_translated = translated_data.get('content_translated')
                    article.detected_language = translated_data.get('detected_language')
                    self.pipeline_stats['translations_completed'] += 1
                
                # Analysis phase
                analyzed_article = await self.analyzer._analyze_article(article)
                processed_articles.append(analyzed_article)
                self.pipeline_stats['analyses_completed'] += 1
                
                # Small delay between articles
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error processing article {article.title}: {e}")
                self.pipeline_stats['errors'] += 1
                continue
        
        return processed_articles
    
    async def process_high_priority_articles(self, articles: List[Article]) -> List[Article]:
        """高優先度記事の優先処理"""
        self.logger.info("Processing high priority articles")
        
        # Use optimized batch analysis for high priority
        return await self.analyzer.analyze_articles_batch_optimized(articles, batch_size=3)
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """パイプライン統計情報取得"""
        # Combine stats from sub-services
        translation_stats = self.translator.get_translation_stats()
        analysis_stats = self.analyzer.get_performance_stats()
        
        return {
            'pipeline': self.pipeline_stats,
            'translation': translation_stats,
            'analysis': analysis_stats,
            'configuration': {
                'parallel_processing': self.parallel_processing,
                'batch_size': self.batch_size,
                'max_concurrent_translations': self.max_concurrent_translations,
                'max_concurrent_analyses': self.max_concurrent_analyses
            }
        }
    
    async def test_pipeline(self) -> Dict[str, Any]:
        """パイプラインテスト"""
        test_articles = [
            {
                'title': 'Test Article: AI Development News',
                'content': 'This is a test article about artificial intelligence development and machine learning advances.',
                'url': 'https://test.example.com/ai-news',
                'source': {'name': 'Test Source'},
                'language': 'en',
                'category': 'tech'
            },
            {
                'title': 'テストニュース：日本の経済状況',
                'content': 'これは日本の経済状況に関するテスト記事です。',
                'url': 'https://test.example.com/jp-economy',
                'source': {'name': 'テストソース'},
                'language': 'ja',
                'category': 'economy'
            }
        ]
        
        try:
            start_time = time.time()
            processed_articles = await self.process_articles(test_articles)
            processing_time = time.time() - start_time
            
            return {
                'status': 'success',
                'processed_count': len(processed_articles),
                'processing_time': processing_time,
                'articles': [
                    {
                        'title': article.title,
                        'translated_title': getattr(article, 'title_translated', None),
                        'summary': getattr(article, 'summary', None),
                        'importance_score': getattr(article, 'importance_score', None),
                        'keywords': getattr(article, 'keywords', []),
                        'processed': getattr(article, 'processed', False)
                    }
                    for article in processed_articles
                ]
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def reset_stats(self):
        """統計情報をリセット"""
        self.pipeline_stats = {
            'articles_processed': 0,
            'translations_completed': 0,
            'analyses_completed': 0,
            'cache_hits': 0,
            'errors': 0,
            'total_processing_time': 0,
            'average_time_per_article': 0
        }
        
        # Reset sub-service stats if they have reset methods
        if hasattr(self.analyzer, 'analysis_stats'):
            self.analyzer.analysis_stats = {
                'total_analyzed': 0,
                'cache_hits': 0,
                'api_calls': 0,
                'errors': 0
            }


class PipelineResultProcessor:
    """パイプライン結果処理クラス"""
    
    @staticmethod
    def filter_urgent_articles(articles: List[Article]) -> List[Article]:
        """緊急記事のフィルタリング"""
        return [
            article for article in articles 
            if getattr(article, 'is_urgent', False) or getattr(article, 'importance_score', 0) >= 9
        ]
    
    @staticmethod
    def sort_by_importance(articles: List[Article]) -> List[Article]:
        """重要度順ソート"""
        return sorted(
            articles, 
            key=lambda x: getattr(x, 'importance_score', 5), 
            reverse=True
        )
    
    @staticmethod
    def categorize_articles(articles: List[Article]) -> Dict[str, List[Article]]:
        """カテゴリ別記事分類"""
        categories = {}
        
        for article in articles:
            category = getattr(article, 'detailed_category', getattr(article, 'category', '未分類'))
            if category not in categories:
                categories[category] = []
            categories[category].append(article)
        
        return categories
    
    @staticmethod
    def generate_summary_report(articles: List[Article]) -> Dict[str, Any]:
        """要約レポート生成"""
        if not articles:
            return {'total': 0, 'summary': 'No articles processed'}
        
        total_articles = len(articles)
        urgent_count = len(PipelineResultProcessor.filter_urgent_articles(articles))
        
        # Calculate average importance
        importance_scores = [getattr(a, 'importance_score', 5) for a in articles]
        avg_importance = sum(importance_scores) / len(importance_scores) if importance_scores else 0
        
        # Top keywords
        all_keywords = []
        for article in articles:
            keywords = getattr(article, 'keywords', [])
            all_keywords.extend(keywords)
        
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_articles': total_articles,
            'urgent_articles': urgent_count,
            'average_importance': round(avg_importance, 2),
            'top_keywords': top_keywords,
            'categories': list(PipelineResultProcessor.categorize_articles(articles).keys())
        }