"""
Article Deduplication Module
記事重複除去モジュール - URLハッシュと内容類似度による重複検出・除去
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hashlib
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
import difflib
import re

from models.article import Article
from utils.cache_manager import get_cache_manager


logger = logging.getLogger(__name__)


@dataclass
class DuplicationResult:
    """重複検出結果"""
    unique_articles: List[Article]
    duplicate_count: int
    duplicate_groups: List[List[Article]]
    processing_time: float


class ArticleDeduplicator:
    """記事重複除去クラス"""
    
    def __init__(self):
        self.cache = get_cache_manager()
        
        # 重複判定閾値
        self.url_similarity_threshold = 0.8
        self.content_similarity_threshold = 0.7
        self.title_similarity_threshold = 0.8
        
        # キャッシュ期間（30日）
        self.cache_expire = 86400 * 30
    
    def deduplicate(self, articles: List[Article]) -> DuplicationResult:
        """記事リストから重複を除去"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting deduplication for {len(articles)} articles")
            
            # URLハッシュによる高速重複検出
            url_deduped = self._deduplicate_by_url(articles)
            logger.debug(f"URL deduplication: {len(articles)} -> {len(url_deduped)}")
            
            # 内容類似度による重複検出
            content_deduped, duplicate_groups = self._deduplicate_by_content(url_deduped)
            logger.debug(f"Content deduplication: {len(url_deduped)} -> {len(content_deduped)}")
            
            # 過去記事との重複チェック
            final_articles = self._check_historical_duplicates(content_deduped)
            logger.debug(f"Historical deduplication: {len(content_deduped)} -> {len(final_articles)}")
            
            # 重複キャッシュを更新
            self._update_duplicate_cache(final_articles)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            duplicate_count = len(articles) - len(final_articles)
            
            result = DuplicationResult(
                unique_articles=final_articles,
                duplicate_count=duplicate_count,
                duplicate_groups=duplicate_groups,
                processing_time=processing_time
            )
            
            logger.info(f"Deduplication completed: {duplicate_count} duplicates removed "
                       f"in {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Deduplication failed: {e}")
            # エラー時は元の記事リストを返す
            return DuplicationResult(
                unique_articles=articles,
                duplicate_count=0,
                duplicate_groups=[],
                processing_time=(datetime.now() - start_time).total_seconds()
            )
    
    def _deduplicate_by_url(self, articles: List[Article]) -> List[Article]:
        """URLによる重複除去"""
        seen_urls: Set[str] = set()
        seen_url_hashes: Set[str] = set()
        unique_articles = []
        
        for article in articles:
            # 正規化されたURL
            normalized_url = self._normalize_url(article.url)
            url_hash = hashlib.md5(normalized_url.encode()).hexdigest()
            
            # URL完全一致チェック
            if normalized_url in seen_urls:
                logger.debug(f"Duplicate URL found: {article.url}")
                continue
            
            # URLハッシュチェック
            if url_hash in seen_url_hashes:
                logger.debug(f"Duplicate URL hash found: {article.url}")
                continue
            
            # 類似URLチェック
            if self._is_similar_url_exists(normalized_url, seen_urls):
                logger.debug(f"Similar URL found: {article.url}")
                continue
            
            seen_urls.add(normalized_url)
            seen_url_hashes.add(url_hash)
            unique_articles.append(article)
        
        return unique_articles
    
    def _deduplicate_by_content(self, articles: List[Article]) -> Tuple[List[Article], List[List[Article]]]:
        """内容による重複除去"""
        unique_articles = []
        duplicate_groups = []
        processed_indices = set()
        
        for i, article in enumerate(articles):
            if i in processed_indices:
                continue
            
            # 類似記事グループを検索
            similar_group = [article]
            processed_indices.add(i)
            
            for j, other_article in enumerate(articles[i+1:], i+1):
                if j in processed_indices:
                    continue
                
                if self._are_articles_similar(article, other_article):
                    similar_group.append(other_article)
                    processed_indices.add(j)
            
            # グループから最も品質の高い記事を選択
            best_article = self._select_best_article(similar_group)
            unique_articles.append(best_article)
            
            # 重複グループが2件以上の場合は記録
            if len(similar_group) > 1:
                duplicate_groups.append(similar_group)
                logger.debug(f"Found duplicate group with {len(similar_group)} articles")
        
        return unique_articles, duplicate_groups
    
    def _check_historical_duplicates(self, articles: List[Article]) -> List[Article]:
        """過去記事との重複チェック"""
        unique_articles = []
        
        for article in articles:
            url_hash = hashlib.md5(self._normalize_url(article.url).encode()).hexdigest()
            
            # キャッシュから過去の記事をチェック
            cache_key = f"url_hash:{url_hash}"
            if not self.cache.exists(cache_key, 'dedup'):
                unique_articles.append(article)
                # 新しい記事をキャッシュに保存
                self.cache.set(cache_key, article.url, expire=self.cache_expire, category='dedup')
            else:
                cached_url = self.cache.get(cache_key, 'dedup')
                logger.debug(f"Historical duplicate found: {article.url} (cached: {cached_url})")
        
        return unique_articles
    
    def _normalize_url(self, url: str) -> str:
        """URL正規化"""
        if not url:
            return ""
        
        # 小文字に変換
        normalized = url.lower()
        
        # プロトコル統一
        normalized = re.sub(r'^https?://', 'https://', normalized)
        
        # www.の統一
        normalized = re.sub(r'https://www\.', 'https://', normalized)
        
        # 末尾スラッシュの除去
        normalized = normalized.rstrip('/')
        
        # URLパラメータの除去（utm_source等）
        normalized = re.sub(r'[?&]utm_[^&]*', '', normalized)
        normalized = re.sub(r'[?&]ref=[^&]*', '', normalized)
        normalized = re.sub(r'[?&]source=[^&]*', '', normalized)
        
        # 重複するクエリセパレータの除去
        normalized = re.sub(r'[?&]+', lambda m: '?' if m.group().startswith('?') else '&', normalized)
        
        return normalized
    
    def _is_similar_url_exists(self, url: str, existing_urls: Set[str]) -> bool:
        """類似URLの存在チェック"""
        for existing_url in existing_urls:
            similarity = difflib.SequenceMatcher(None, url, existing_url).ratio()
            if similarity > self.url_similarity_threshold:
                return True
        return False
    
    def _are_articles_similar(self, article1: Article, article2: Article) -> bool:
        """記事の類似性判定"""
        # タイトル類似度チェック（属性名を修正）
        title1 = (getattr(article1, 'translated_title', None) or article1.title or "").lower()
        title2 = (getattr(article2, 'translated_title', None) or article2.title or "").lower()
        
        title_similarity = difflib.SequenceMatcher(None, title1, title2).ratio()
        if title_similarity > self.title_similarity_threshold:
            return True
        
        # 内容類似度チェック
        content1 = self._extract_content_for_comparison(article1)
        content2 = self._extract_content_for_comparison(article2)
        
        if content1 and content2:
            content_similarity = difflib.SequenceMatcher(None, content1, content2).ratio()
            if content_similarity > self.content_similarity_threshold:
                return True
        
        # 同一ソース・同一時間の記事チェック
        try:
            if (article1.source == article2.source and 
                article1.published_at and article2.published_at and
                isinstance(article1.published_at, datetime) and isinstance(article2.published_at, datetime) and
                abs((article1.published_at - article2.published_at).total_seconds()) < 3600):  # 1時間以内
                
                # タイトルに共通キーワードが多い場合
                common_keywords = self._get_common_keywords(title1, title2)
                if len(common_keywords) >= 3:  # 3つ以上の共通キーワード
                    return True
        except (TypeError, AttributeError):
            pass
        
        return False
    
    def _extract_content_for_comparison(self, article: Article) -> str:
        """比較用の内容抽出"""
        content = getattr(article, 'translated_content', None) or getattr(article, 'content', "") or ""
        summary = getattr(article, 'summary', "") or ""
        
        # 長い方を使用（ただし最初の500文字まで）
        comparison_text = content if len(content) > len(summary) else summary
        
        # 正規化
        comparison_text = re.sub(r'\s+', ' ', comparison_text.lower())
        comparison_text = re.sub(r'[^\w\s]', '', comparison_text)
        
        return comparison_text[:500]
    
    def _get_common_keywords(self, text1: str, text2: str) -> Set[str]:
        """共通キーワード抽出"""
        # Input validation and normalization
        text1 = str(text1) if text1 is not None else ''
        text2 = str(text2) if text2 is not None else ''
        
        # 簡単な単語分割（日本語対応は制限的）
        words1 = set(re.findall(r'\b\w{3,}\b', text1))  # 3文字以上の単語
        words2 = set(re.findall(r'\b\w{3,}\b', text2))
        
        # ストップワード除去
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 
            'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 
            'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy',
            'この', 'その', 'あの', 'どの', 'です', 'ます', 'である', 'だった'
        }
        
        words1 = words1 - stop_words
        words2 = words2 - stop_words
        
        return words1.intersection(words2)
    
    def _select_best_article(self, similar_articles: List[Article]) -> Article:
        """類似記事グループから最適な記事を選択"""
        if len(similar_articles) == 1:
            return similar_articles[0]
        
        # 評価スコア計算
        scored_articles = []
        
        for article in similar_articles:
            score = 0
            
            # 内容の長さ（長い方が詳細）
            content_length = len(article.content or "")
            score += min(content_length / 1000, 5)  # 最大5点
            
            # 翻訳済みかどうか
            if getattr(article, 'translated_title', None) or getattr(article, 'translated_content', None):
                score += 2
            
            # 重要度スコア
            score += (getattr(article, 'importance_score', None) or 5) / 2
            
            # 新しい記事を優先
            published_at = getattr(article, 'published_at', None)
            if published_at and isinstance(published_at, datetime):
                hours_old = (datetime.now() - published_at).total_seconds() / 3600
                if hours_old < 24:
                    score += 2
                elif hours_old < 72:
                    score += 1
            
            # 信頼できるソース
            trusted_sources = ['bbc', 'reuters', 'ap', 'nhk', 'asahi', 'nikkei']
            source_name = getattr(article, 'source', '') or getattr(article, 'source_name', '') or ''
            if source_name and any(source in source_name.lower() for source in trusted_sources):
                score += 1
            
            scored_articles.append((score, article))
        
        # 最高スコアの記事を選択
        scored_articles.sort(key=lambda x: x[0], reverse=True)
        selected_article = scored_articles[0][1]
        
        logger.debug(f"Selected best article from {len(similar_articles)} similar articles: "
                    f"{selected_article.title[:50]}...")
        
        return selected_article
    
    def _update_duplicate_cache(self, articles: List[Article]):
        """重複キャッシュの更新"""
        for article in articles:
            url_hash = hashlib.md5(self._normalize_url(article.url).encode()).hexdigest()
            cache_key = f"url_hash:{url_hash}"
            
            # URLハッシュをキャッシュに保存
            self.cache.set(cache_key, article.url, expire=self.cache_expire, category='dedup')
            
            # 内容ハッシュもキャッシュ
            content_for_hash = self._extract_content_for_comparison(article)
            if content_for_hash:
                content_hash = hashlib.md5(content_for_hash.encode()).hexdigest()
                content_cache_key = f"content_hash:{content_hash}"
                self.cache.set(content_cache_key, article.url, expire=self.cache_expire, category='dedup')
    
    def get_stats(self) -> Dict[str, any]:
        """重複除去統計情報を取得"""
        try:
            cache_stats = self.cache.get_stats()
            dedup_entries = cache_stats.get('categories', {}).get('dedup', {}).get('count', 0)
            
            return {
                'cached_urls': dedup_entries,
                'url_similarity_threshold': self.url_similarity_threshold,
                'content_similarity_threshold': self.content_similarity_threshold,
                'title_similarity_threshold': self.title_similarity_threshold,
                'cache_expire_days': self.cache_expire // 86400
            }
            
        except Exception as e:
            logger.error(f"Failed to get deduplication stats: {e}")
            return {}
    
    def clear_cache(self) -> int:
        """重複除去キャッシュをクリア"""
        return self.cache.clear_category('dedup')