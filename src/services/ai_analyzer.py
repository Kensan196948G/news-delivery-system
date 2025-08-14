"""
AI analysis service using Claude API for article analysis and summarization
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import time

import anthropic

from utils.config import get_config
from utils.rate_limiter import RateLimiter
from models.article import Article


logger = logging.getLogger(__name__)


class AIAnalysisError(Exception):
    """AI analysis specific error"""
    pass


class ClaudeAnalyzer:
    """Claude API analyzer for news articles"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.rate_limiter = RateLimiter()
        
        # Initialize Claude client
        api_key = self.config.get_api_key('claude')
        if not api_key:
            raise AIAnalysisError("Anthropic API key not provided")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        
        # Configuration
        self.model = self.config.get('ai_analysis', 'claude', 'model', default='claude-3-sonnet-20240229')
        self.max_tokens = self.config.get('ai_analysis', 'claude', 'max_tokens', default=4096)
        self.temperature = self.config.get('ai_analysis', 'claude', 'temperature', default=0.3)
        
        # Analysis configuration
        self.summary_min_length = self.config.get('ai_analysis', 'claude', 'summary_length', 'min', default=200)
        self.summary_max_length = self.config.get('ai_analysis', 'claude', 'summary_length', 'max', default=250)
        self.max_keywords = self.config.get('ai_analysis', 'claude', 'max_keywords', default=5)
        self.importance_min = self.config.get('ai_analysis', 'claude', 'importance_scale', 'min', default=1)
        self.importance_max = self.config.get('ai_analysis', 'claude', 'importance_scale', 'max', default=10)
        
        # Initialize analysis cache
        self.analysis_cache = {}
        self.cache_ttl = 3600 * 24  # 24 hours cache
        
        # Performance tracking
        self.analysis_stats = {
            'total_analyzed': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'errors': 0
        }
    
    async def analyze_articles(self, articles: List[Article]) -> List[Article]:
        """Analyze multiple articles"""
        analyzed_articles = []
        
        for article in articles:
            try:
                # Skip if already analyzed
                if article.processed and article.summary and article.importance_score > 0:
                    analyzed_articles.append(article)
                    continue
                
                # Check rate limits
                await self.rate_limiter.wait_if_needed('claude')
                
                # Analyze the article
                analyzed_article = await self._analyze_article(article)
                analyzed_articles.append(analyzed_article)
                
                # Record API usage
                self.rate_limiter.record_request('claude')
                
                # Small delay between requests
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Failed to analyze article '{article.title}': {e}")
                # Add original article even if analysis failed
                analyzed_articles.append(article)
        
        logger.info(f"Analyzed {len([a for a in analyzed_articles if a.summary])} "
                   f"out of {len(articles)} articles")
        
        return analyzed_articles
    
    async def _analyze_article(self, article: Article) -> Article:
        """Analyze a single article using Claude"""
        try:
            # Prepare content for analysis
            content_to_analyze = self._prepare_content_for_analysis(article)
            
            if len(content_to_analyze) < 50:
                logger.warning(f"Article too short for analysis: {article.title}")
                return article
            
            # Check cache first
            cache_key = self._generate_cache_key(content_to_analyze)
            cached_result = self._get_cached_analysis(cache_key)
            
            if cached_result:
                self.analysis_stats['cache_hits'] += 1
                self._update_article_with_analysis(article, cached_result)
                logger.debug(f"Used cached analysis for: {article.title[:50]}...")
                return article
            
            # Create analysis prompt
            prompt = self._create_analysis_prompt(content_to_analyze, getattr(article, 'category', 'general'))
            
            # Call Claude API
            response = await self._call_claude_api(prompt)
            self.analysis_stats['api_calls'] += 1
            
            if response:
                # Parse response and update article
                analysis_result = self._parse_analysis_response(response)
                
                # Cache the result
                self._cache_analysis(cache_key, analysis_result)
                
                self._update_article_with_analysis(article, analysis_result)
                
                logger.debug(f"Analyzed article: {article.title[:50]}...")
            
            self.analysis_stats['total_analyzed'] += 1
            return article
            
        except Exception as e:
            self.analysis_stats['errors'] += 1
            logger.error(f"Article analysis failed: {e}")
            return article
    
    def _generate_cache_key(self, content: str) -> str:
        """Generate cache key for analysis"""
        import hashlib
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _get_cached_analysis(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis result"""
        if cache_key in self.analysis_cache:
            cached_item = self.analysis_cache[cache_key]
            
            # Check if cache is still valid
            import time
            if time.time() - cached_item['timestamp'] < self.cache_ttl:
                return cached_item['analysis']
            else:
                # Remove expired cache
                del self.analysis_cache[cache_key]
        
        return None
    
    def _cache_analysis(self, cache_key: str, analysis: Dict[str, Any]):
        """Cache analysis result"""
        import time
        self.analysis_cache[cache_key] = {
            'analysis': analysis,
            'timestamp': time.time()
        }
        
        # Limit cache size (keep only 1000 most recent)
        if len(self.analysis_cache) > 1000:
            # Remove oldest 100 entries
            sorted_items = sorted(
                self.analysis_cache.items(),
                key=lambda x: x[1]['timestamp']
            )
            for key, _ in sorted_items[:100]:
                del self.analysis_cache[key]
    
    def _prepare_content_for_analysis(self, article: Article) -> str:
        """Prepare article content for Claude analysis"""
        # Use translated content if available, otherwise original
        title = article.title_translated or article.title
        content = article.content_translated or article.content
        
        # Limit content length to avoid token limits
        max_content_length = 3000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        return f"タイトル: {title}\n\n内容: {content}"
    
    def _create_analysis_prompt(self, content: str, category: str) -> str:
        """Create analysis prompt for Claude"""
        prompt = f"""
以下のニュース記事を分析し、JSON形式で結果を返してください。

記事カテゴリ: {category}
記事内容:
{content}

以下の項目について詳細に分析してください：

1. 重要度スコア (1-10): 記事の重要性を1から10で評価
2. 要約 ({self.summary_min_length or 200}-{self.summary_max_length or 250}文字): 記事の要点を簡潔にまとめる
3. キーワード (最大{self.max_keywords or 5}個): 記事の重要なキーワードを抽出
4. センチメント (-1.0から1.0): 記事の感情的な調子を数値化
5. 緊急性判定 (true/false): 緊急対応が必要かどうか
6. 影響範囲 (local/national/international): 記事の影響範囲
7. 信頼性スコア (1-10): 情報の信頼性評価
8. カテゴリ分類: より詳細なカテゴリ分類

重要度スコア評価基準:
- 1-3: 一般的なニュース（日常的な話題、軽微な事件）
- 4-6: 注目すべきニュース（地域的影響、業界ニュース）
- 7-8: 重要なニュース（国内重要事件、経済影響大）
- 9-10: 極めて重要/緊急性の高いニュース（国際問題、災害、重大セキュリティ問題）

特別な評価基準:
- セキュリティ関連: CVE情報、脆弱性、サイバー攻撃は+2点
- 災害・安全: 人命に関わる情報は+1-3点
- 経済・政治: 市場に大きな影響を与える情報は+1-2点
- AI・技術: 技術革新や重要なIT関連ニュースは基準通り

信頼性評価基準:
- 1-3: 未確認情報、噂レベル
- 4-6: 一次情報源不明、複数ソース未確認
- 7-8: 信頼できるメディア、公的機関発表
- 9-10: 一次情報源、公式発表、確認済み事実

回答は以下のJSON形式で返してください：
{{
    "importance_score": 数値,
    "summary": "要約文",
    "keywords": ["キーワード1", "キーワード2", ...],
    "sentiment_score": 数値,
    "is_urgent": boolean,
    "impact_scope": "local/national/international",
    "reliability_score": 数値,
    "detailed_category": "詳細カテゴリ",
    "reasoning": "評価の理由",
    "risk_factors": ["リスク要因1", "リスク要因2", ...],
    "action_required": "必要な対応行動"
}}
"""
        return prompt
    
    async def _call_claude_api(self, prompt: str) -> Optional[str]:
        """Call Claude API with error handling"""
        try:
            # Use asyncio to run synchronous Claude API call
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                None,
                self._sync_claude_call,
                prompt
            )
            
            return response.content[0].text if response and response.content else None
            
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            return None
    
    def _sync_claude_call(self, prompt: str) -> anthropic.types.Message:
        """Synchronous Claude API call"""
        return self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse Claude's analysis response"""
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = response[json_start:json_end]
                analysis = json.loads(json_text)
                
                # Validate and clean up the analysis
                return self._validate_analysis_result(analysis)
            else:
                logger.warning("No valid JSON found in Claude response")
                return {}
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error parsing analysis response: {e}")
            return {}
    
    def _validate_analysis_result(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean up analysis result"""
        validated = {}
        
        # Importance score (1-10)
        importance = analysis.get('importance_score', 5)
        validated['importance_score'] = max(self.importance_min, 
                                          min(self.importance_max, int(importance)))
        
        # Summary (length check)
        summary = analysis.get('summary', '')
        if len(summary) < self.summary_min_length:
            summary += " (要約が短いため、詳細は元記事をご参照ください。)"
        elif len(summary) > self.summary_max_length + 50:
            summary = summary[:self.summary_max_length] + "..."
        validated['summary'] = summary
        
        # Keywords (limit count)
        keywords = analysis.get('keywords', [])
        if isinstance(keywords, list):
            validated['keywords'] = keywords[:self.max_keywords]
        else:
            validated['keywords'] = []
        
        # Sentiment score (-1.0 to 1.0)
        sentiment = analysis.get('sentiment_score', 0.0)
        validated['sentiment_score'] = max(-1.0, min(1.0, float(sentiment)))
        
        # Urgency flag
        validated['is_urgent'] = bool(analysis.get('is_urgent', False))
        
        # Impact scope validation
        impact_scope = analysis.get('impact_scope', 'local')
        valid_scopes = ['local', 'national', 'international']
        validated['impact_scope'] = impact_scope if impact_scope in valid_scopes else 'local'
        
        # Reliability score (1-10)
        reliability = analysis.get('reliability_score', 7)
        validated['reliability_score'] = max(1, min(10, int(reliability)))
        
        # Detailed category
        validated['detailed_category'] = analysis.get('detailed_category', '未分類')
        
        # Risk factors
        risk_factors = analysis.get('risk_factors', [])
        if isinstance(risk_factors, list):
            validated['risk_factors'] = risk_factors[:5]  # Limit to 5 risk factors
        else:
            validated['risk_factors'] = []
        
        # Action required
        validated['action_required'] = analysis.get('action_required', '継続監視')
        
        # Additional info
        validated['reasoning'] = analysis.get('reasoning', '')
        
        return validated
    
    def _update_article_with_analysis(self, article: Article, analysis: Dict[str, Any]):
        """Update article with analysis results"""
        article.importance_score = analysis.get('importance_score', 5)
        article.summary = analysis.get('summary', '')
        article.keywords = analysis.get('keywords', [])
        article.sentiment_score = analysis.get('sentiment_score', 0.0)
        
        # Enhanced analysis fields
        article.impact_scope = analysis.get('impact_scope', 'local')
        article.reliability_score = analysis.get('reliability_score', 7)
        article.detailed_category = analysis.get('detailed_category', '未分類')
        article.risk_factors = analysis.get('risk_factors', [])
        article.action_required = analysis.get('action_required', '継続監視')
        article.analysis_reasoning = analysis.get('reasoning', '')
        
        # Update urgency based on analysis and existing criteria
        analysis_urgent = analysis.get('is_urgent', False)
        score_urgent = article.importance_score >= 9
        cvss_urgent = hasattr(article, 'cvss_score') and article.cvss_score and article.cvss_score >= 9.0
        reliability_urgent = article.reliability_score >= 9 and article.importance_score >= 8
        
        article.is_urgent = analysis_urgent or score_urgent or cvss_urgent or reliability_urgent
        article.processed = True
        
        # Set analysis timestamp
        from datetime import datetime
        article.analyzed_at = datetime.now().isoformat()
    
    async def analyze_vulnerability_batch(self, vulnerabilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze security vulnerabilities in batch"""
        analyzed_vulnerabilities = []
        
        for vuln in vulnerabilities:
            try:
                # Check rate limits
                await self.rate_limiter.wait_if_needed('claude')
                
                # Analyze vulnerability
                analyzed_vuln = await self._analyze_vulnerability(vuln)
                analyzed_vulnerabilities.append(analyzed_vuln)
                
                # Record API usage
                self.rate_limiter.record_request('claude')
                
                # Small delay
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to analyze vulnerability {vuln.get('cve_id', 'unknown')}: {e}")
                analyzed_vulnerabilities.append(vuln)
        
        return analyzed_vulnerabilities
    
    async def _analyze_vulnerability(self, vulnerability: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single vulnerability"""
        try:
            cve_id = vulnerability.get('cve_id', '')
            description = vulnerability.get('description', '')
            cvss_score = vulnerability.get('cvss_score', 0.0)
            
            if not description or len(description) < 50:
                return vulnerability
            
            prompt = f"""
以下のセキュリティ脆弱性情報を分析し、JSON形式で結果を返してください。

CVE ID: {cve_id}
CVSSスコア: {cvss_score}
説明: {description[:1000]}

以下について分析してください：
1. 影響度評価 (1-10): システムへの潜在的影響
2. 緊急度評価 (1-10): 対応の緊急性
3. 要約 (200文字以内): 脆弱性の要点
4. 対策の重要性 (1-10): パッチ適用の重要度

JSON形式で回答してください：
{{
    "impact_score": 数値,
    "urgency_score": 数値,
    "summary": "要約",
    "patch_priority": 数値,
    "risk_assessment": "リスク評価"
}}
"""
            
            response = await self._call_claude_api(prompt)
            
            if response:
                analysis = self._parse_analysis_response(response)
                vulnerability.update(analysis)
            
            return vulnerability
            
        except Exception as e:
            logger.error(f"Vulnerability analysis failed: {e}")
            return vulnerability
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get analysis statistics"""
        remaining_requests = self.rate_limiter.get_remaining_requests('claude')
        
        return {
            'service_enabled': self.is_analysis_enabled(),
            'model': self.model,
            'remaining_requests': remaining_requests,
            'configuration': {
                'max_tokens': self.max_tokens,
                'temperature': self.temperature,
                'summary_length': f"{self.summary_min_length}-{self.summary_max_length}",
                'max_keywords': self.max_keywords
            }
        }
    
    def is_analysis_enabled(self) -> bool:
        """Check if AI analysis is enabled and configured"""
        return (
            self.config.get('ai_analysis.claude.enabled', True) and
            self.config.get_api_key('claude') is not None
        )
    
    async def analyze_articles_batch_optimized(self, articles: List[Article], batch_size: int = 5) -> List[Article]:
        """Optimized batch analysis with intelligent prioritization"""
        analyzed_articles = []
        
        # Separate articles by priority
        urgent_articles = [a for a in articles if getattr(a, 'is_urgent', False)]
        high_priority = [a for a in articles if getattr(a, 'importance_score', 5) >= 8 and a not in urgent_articles]
        normal_articles = [a for a in articles if a not in urgent_articles and a not in high_priority]
        
        # Process in order of priority
        priority_batches = [
            ("URGENT", urgent_articles),
            ("HIGH", high_priority), 
            ("NORMAL", normal_articles)
        ]
        
        for priority_name, article_batch in priority_batches:
            if not article_batch:
                continue
                
            logger.info(f"Processing {len(article_batch)} {priority_name} priority articles")
            
            # Process in smaller batches
            for i in range(0, len(article_batch), batch_size):
                batch = article_batch[i:i + batch_size]
                batch_tasks = []
                
                for article in batch:
                    if not getattr(article, 'processed', False):
                        batch_tasks.append(self._analyze_article(article))
                    else:
                        batch_tasks.append(asyncio.create_task(self._return_processed_article(article)))
                
                # Process batch concurrently with rate limiting
                semaphore = asyncio.Semaphore(3)  # Limit concurrent API calls
                
                async def analyze_with_semaphore(task):
                    async with semaphore:
                        return await task
                
                batch_results = await asyncio.gather(
                    *[analyze_with_semaphore(task) for task in batch_tasks],
                    return_exceptions=True
                )
                
                # Add successful results
                for result in batch_results:
                    if isinstance(result, Article):
                        analyzed_articles.append(result)
                    else:
                        logger.error(f"Batch analysis error: {result}")
                
                # Small delay between batches to respect rate limits
                if i + batch_size < len(article_batch):
                    await asyncio.sleep(1.0)
        
        logger.info(f"Batch analysis completed: {len(analyzed_articles)} articles processed")
        return analyzed_articles
    
    async def _return_processed_article(self, article: Article) -> Article:
        """Return already processed article"""
        self.analysis_stats['cache_hits'] += 1
        return article
    
    async def create_daily_summary(self, articles: List[Article]) -> str:
        """Create a daily summary of all articles"""
        try:
            if not articles:
                return "本日収集された記事はありません。"
            
            # Prepare article summaries for Claude
            article_summaries = []
            for article in articles:
                summary = article.summary or article.title
                importance = getattr(article, 'importance_score', 5)
                urgency = "【緊急】" if getattr(article, 'is_urgent', False) else ""
                article_summaries.append(f"・{urgency}{summary} (重要度: {importance})")
            
            articles_text = "\n".join(article_summaries[:20])  # Limit to top 20
            
            prompt = f"""
以下の記事リストから、今日のニュースの全体的な要約を300文字以内で作成してください。
重要なトピックや傾向を含めてください。

本日の記事一覧:
{articles_text}

要約:
"""
            
            response = await self._call_claude_api(prompt)
            return response if response else "要約の生成に失敗しました。"
            
        except Exception as e:
            logger.error(f"Failed to create daily summary: {e}")
            return "要約の生成中にエラーが発生しました。"
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        cache_hit_rate = 0
        if self.analysis_stats['total_analyzed'] > 0:
            cache_hit_rate = (self.analysis_stats['cache_hits'] / self.analysis_stats['total_analyzed']) * 100
        
        return {
            **self.analysis_stats,
            'cache_hit_rate_percent': round(cache_hit_rate, 2),
            'cache_size': len(self.analysis_cache),
            'average_api_calls_per_article': round(
                self.analysis_stats['api_calls'] / max(self.analysis_stats['total_analyzed'], 1), 2
            ),
            'error_rate_percent': round(
                (self.analysis_stats['errors'] / max(self.analysis_stats['total_analyzed'], 1)) * 100, 2
            )
        }