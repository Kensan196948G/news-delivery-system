"""
Analyzer Service - Wrapper for AI analysis functionality
ニュース記事AI分析サービス
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .ai_analyzer import ClaudeAnalyzer, AIAnalysisError
from models.article import Article
from utils.config import get_config
from utils.logger import setup_logger


class AnalyzerService:
    """
    Main analyzer service that coordinates AI analysis of news articles
    ニュース記事分析サービスのメインクラス
    """
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = setup_logger(__name__)
        
        # Initialize Claude analyzer
        try:
            self.claude_analyzer = ClaudeAnalyzer(self.config)
            self.logger.info("Claude analyzer initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Claude analyzer: {e}")
            self.claude_analyzer = None
    
    async def analyze_articles(self, articles: List[Article]) -> List[Article]:
        """
        Analyze a list of articles using AI
        記事リストのAI分析
        """
        if not articles:
            self.logger.info("No articles to analyze")
            return []
        
        if not self.claude_analyzer:
            self.logger.warning("Claude analyzer not available, returning articles without analysis")
            return articles
        
        self.logger.info(f"Starting analysis of {len(articles)} articles")
        
        analyzed_articles = []
        
        try:
            # Process articles in batches to manage API rate limits
            batch_size = self.config.get('ai_analysis', 'batch_size', default=5)
            
            for i in range(0, len(articles), batch_size):
                batch = articles[i:i + batch_size]
                self.logger.info(f"Analyzing batch {i//batch_size + 1}/{(len(articles) + batch_size - 1)//batch_size}")
                
                # Process batch with Claude
                batch_results = await self._analyze_batch(batch)
                analyzed_articles.extend(batch_results)
                
                # Add delay between batches to respect rate limits
                if i + batch_size < len(articles):
                    delay = self.config.get('ai_analysis', 'batch_delay', default=1.0)
                    await asyncio.sleep(delay)
            
            self.logger.info(f"Analysis completed for {len(analyzed_articles)} articles")
            
        except Exception as e:
            self.logger.error(f"Error during article analysis: {e}")
            # Return original articles if analysis fails
            return articles
        
        return analyzed_articles
    
    async def _analyze_batch(self, articles: List[Article]) -> List[Article]:
        """
        Analyze a batch of articles
        記事バッチの分析
        """
        tasks = []
        
        for article in articles:
            task = self._analyze_single_article(article)
            tasks.append(task)
        
        # Execute all analysis tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        analyzed_articles = []
        for i, result in enumerate(results):
            if isinstance(result, Article):
                analyzed_articles.append(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Failed to analyze article {i}: {result}")
                # Return original article if analysis fails
                analyzed_articles.append(articles[i])
            else:
                # Fallback
                analyzed_articles.append(articles[i])
        
        return analyzed_articles
    
    async def _analyze_single_article(self, article: Article) -> Article:
        """
        Analyze a single article using Claude
        単一記事のClaude分析
        """
        try:
            # Use existing Claude analyzer
            analyzed_data = await self.claude_analyzer.analyze_article_content(
                title=article.title or "",
                content=article.content or "",
                url=article.url or "",
                category=article.category or ""
            )
            
            # Update article with analysis results
            if analyzed_data:
                article.summary = analyzed_data.get('summary', '')
                article.importance_score = analyzed_data.get('importance_score', 5)
                article.keywords = analyzed_data.get('keywords', [])
                article.sentiment = analyzed_data.get('sentiment', 'neutral')
                article.key_points = analyzed_data.get('key_points', [])
                article.category_ai = analyzed_data.get('category', '')
                
                # Add analysis metadata
                article.analysis_metadata = {
                    'analyzed_at': datetime.now().isoformat(),
                    'analyzer_version': 'claude-3-sonnet',
                    'analysis_method': 'ai_analyzer'
                }
                
                self.logger.debug(f"Article analyzed successfully: {article.title[:50]}...")
            
        except AIAnalysisError as e:
            self.logger.warning(f"AI analysis failed for article {article.url}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error analyzing article {article.url}: {e}")
        
        return article
    
    async def analyze_for_emergency(self, articles: List[Article]) -> List[Article]:
        """
        Analyze articles specifically for emergency/high-priority content
        緊急記事の優先分析
        """
        if not self.claude_analyzer:
            return articles
        
        self.logger.info(f"Emergency analysis for {len(articles)} articles")
        
        emergency_analyzed = []
        
        for article in articles:
            try:
                # Quick emergency analysis
                analysis = await self.claude_analyzer.quick_emergency_analysis(
                    title=article.title or "",
                    content=article.content or "",
                    category=article.category or ""
                )
                
                if analysis:
                    article.importance_score = analysis.get('importance_score', 5)
                    article.urgency_level = analysis.get('urgency_level', 'normal')
                    article.risk_level = analysis.get('risk_level', 'low')
                    article.emergency_summary = analysis.get('emergency_summary', '')
                
                emergency_analyzed.append(article)
                
            except Exception as e:
                self.logger.error(f"Emergency analysis failed for article: {e}")
                emergency_analyzed.append(article)
        
        return emergency_analyzed
    
    def get_analyzer_status(self) -> Dict[str, Any]:
        """
        Get current analyzer status
        分析器の状態取得
        """
        status = {
            'service': 'AnalyzerService',
            'claude_analyzer': {
                'available': self.claude_analyzer is not None,
                'model': getattr(self.claude_analyzer, 'model', 'unknown') if self.claude_analyzer else None,
            },
            'last_check': datetime.now().isoformat()
        }
        
        if self.claude_analyzer:
            try:
                # Get additional status from Claude analyzer if available
                claude_status = getattr(self.claude_analyzer, 'get_status', lambda: {})()
                status['claude_analyzer'].update(claude_status)
            except Exception as e:
                status['claude_analyzer']['status_error'] = str(e)
        
        return status