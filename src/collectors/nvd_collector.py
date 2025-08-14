"""
NVD Collector
NVD (National Vulnerability Database) からの脆弱性情報収集
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..models.article import Article, ArticleCategory, ArticleLanguage
from .base_collector import BaseCollector


class NVDCollector(BaseCollector):
    """NVD (National Vulnerability Database) からの脆弱性情報収集"""

    def __init__(self, config, logger):
        super().__init__(config, logger, "nvd")
        self.base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"

        # NVD固有設定
        self.cvss_threshold = config.get(
            "news_sources", "nvd", "cvss_threshold", default=7.0
        )
        self.daily_limit = config.get(
            "news_sources", "nvd", "rate_limit_per_day", default=50
        )
        self.request_count = 0

        # 重要度マッピング
        self.severity_mapping = {"LOW": 1, "MEDIUM": 4, "HIGH": 7, "CRITICAL": 10}

        # CWEカテゴリマッピング
        self.cwe_categories = {
            "CWE-79": "XSS",  # Cross-site Scripting
            "CWE-89": "SQLインジェクション",
            "CWE-352": "CSRF",
            "CWE-22": "パストラバーサル",
            "CWE-94": "コードインジェクション",
            "CWE-78": "OSコマンドインジェクション",
        }

    async def collect(
        self, days_back: int = 7, cvss_severity: str = "HIGH,CRITICAL"
    ) -> List[Article]:
        """NVDから脆弱性情報を収集"""

        # 日次制限チェック
        if self.request_count >= self.daily_limit:
            self.logger.warning(f"NVD daily limit reached: {self.daily_limit}")
            return []

        # 日付範囲計算
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # リクエストパラメータ
        params = {
            "pubStartDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "pubEndDate": end_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "resultsPerPage": 100,
            "cvssV3Severity": cvss_severity,
        }

        try:
            self.logger.info(
                f"Fetching NVD vulnerabilities: {days_back} days back, severity={cvss_severity}"
            )

            # APIリクエスト実行（タイムアウト延長）
            data = await self.fetch_with_cache(
                self.base_url, params, cache_ttl=7200
            )  # 2時間キャッシュ

            if not data:
                return []

            # レスポンス処理
            vulnerabilities = data.get("vulnerabilities", [])
            total_results = data.get("totalResults", 0)

            self.logger.info(
                f"NVD returned {len(vulnerabilities)} vulnerabilities (total: {total_results})"
            )

            # 脆弱性変換
            articles = self._process_vulnerabilities(vulnerabilities)

            self.request_count += 1
            self.logger.info(
                f"NVD: Successfully collected {len(articles)} vulnerability articles"
            )

            return articles

        except Exception as e:
            self.logger.error(f"NVD collection failed: {e}")
            return []

    async def collect_critical_vulnerabilities(
        self, days_back: int = 3
    ) -> List[Article]:
        """緊急の重要脆弱性のみを収集（CVSS 9.0以上）"""
        return await self.collect(days_back=days_back, cvss_severity="CRITICAL")

    async def collect_recent_high_vulnerabilities(
        self, days_back: int = 14
    ) -> List[Article]:
        """最近の高危険度脆弱性を収集"""
        return await self.collect(days_back=days_back, cvss_severity="HIGH,CRITICAL")

    def _process_vulnerabilities(
        self, vulnerabilities: List[Dict[str, Any]]
    ) -> List[Article]:
        """脆弱性データの処理・変換"""
        processed_articles = []

        for vuln_data in vulnerabilities:
            try:
                # 基本情報抽出
                cve = vuln_data.get("cve", {})
                cve_id = cve.get("id", "")

                if not cve_id:
                    continue

                # 記事オブジェクト作成
                article = self._create_vulnerability_article(cve, cve_id)

                if article:
                    processed_articles.append(article)

            except Exception as e:
                self.logger.warning(f"Failed to process vulnerability: {e}")
                continue

        # CVSSスコア順にソート
        processed_articles.sort(key=lambda x: x.cvss_score or 0, reverse=True)

        self.logger.debug(f"Processed {len(processed_articles)} valid vulnerabilities")
        return processed_articles

    def _create_vulnerability_article(
        self, cve: Dict[str, Any], cve_id: str
    ) -> Optional[Article]:
        """脆弱性記事オブジェクトの作成"""
        try:
            # CVSSスコア取得
            cvss_score, cvss_vector, severity = self._extract_cvss_info(cve)

            # 閾値チェック
            if cvss_score < self.cvss_threshold:
                return None

            # 説明取得
            description = self._extract_description(cve)

            # CWE情報取得
            cwe_info = self._extract_cwe_info(cve)

            # 参考リンク取得
            references = self._extract_references(cve)

            # 公開日取得
            published_date = self.parse_date(cve.get("published"))

            # タイトル生成
            title = f"CVE-{cve_id}: {severity} セキュリティ脆弱性 (CVSS {cvss_score})"

            # 重要度スコア計算
            importance_score = self._calculate_importance_score(
                cvss_score, severity, cwe_info
            )

            # 記事内容構築
            content = self._build_vulnerability_content(
                cve_id,
                description,
                cvss_score,
                cvss_vector,
                cwe_info,
                references,
                severity,
            )

            article = Article(
                title=title,
                content=content,
                url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                source="NVD",
                category=ArticleCategory.SECURITY,
                language=ArticleLanguage.ENGLISH,
                published_at=published_date,
                collected_at=datetime.now(),
                # 脆弱性固有情報
                cvss_score=cvss_score,
                cve_id=cve_id,
                importance_score=importance_score,
            )

            return article

        except Exception as e:
            self.logger.error(
                f"Failed to create vulnerability article for {cve_id}: {e}"
            )
            return None

    def _extract_cvss_info(self, cve: Dict[str, Any]) -> tuple:
        """CVSSスコア情報を抽出"""
        cvss_score = 0.0
        cvss_vector = ""
        severity = "UNKNOWN"

        metrics = cve.get("metrics", {})

        # CVSS v3.1を優先、次にv3.0
        if "cvssMetricV31" in metrics and metrics["cvssMetricV31"]:
            cvss_data = metrics["cvssMetricV31"][0]["cvssData"]
            cvss_score = cvss_data.get("baseScore", 0.0)
            cvss_vector = cvss_data.get("vectorString", "")
            severity = cvss_data.get("baseSeverity", "UNKNOWN")

        elif "cvssMetricV30" in metrics and metrics["cvssMetricV30"]:
            cvss_data = metrics["cvssMetricV30"][0]["cvssData"]
            cvss_score = cvss_data.get("baseScore", 0.0)
            cvss_vector = cvss_data.get("vectorString", "")
            severity = cvss_data.get("baseSeverity", "UNKNOWN")

        return cvss_score, cvss_vector, severity

    def _extract_description(self, cve: Dict[str, Any]) -> str:
        """脆弱性の説明を抽出"""
        descriptions = cve.get("descriptions", [])

        for desc in descriptions:
            if desc.get("lang") == "en":
                return desc.get("value", "")

        # 英語がない場合は最初の説明を使用
        if descriptions:
            return descriptions[0].get("value", "")

        return ""

    def _extract_cwe_info(self, cve: Dict[str, Any]) -> List[str]:
        """CWE情報を抽出"""
        cwe_ids = []
        weaknesses = cve.get("weaknesses", [])

        for weakness in weaknesses:
            for desc in weakness.get("description", []):
                if desc.get("lang") == "en":
                    cwe_id = desc.get("value", "")
                    if cwe_id.startswith("CWE-"):
                        cwe_ids.append(cwe_id)

        return cwe_ids

    def _extract_references(self, cve: Dict[str, Any]) -> List[str]:
        """参考リンクを抽出"""
        urls = []
        references = cve.get("references", [])

        for ref in references[:5]:  # 最大5件
            url = ref.get("url", "")
            if url and url.startswith("http"):
                urls.append(url)

        return urls

    def _calculate_importance_score(
        self, cvss_score: float, severity: str, cwe_info: List[str]
    ) -> int:
        """重要度スコア計算"""
        # CVSSスコアベース
        if cvss_score >= 9.0:
            score = 10
        elif cvss_score >= 7.0:
            score = 8
        elif cvss_score >= 4.0:
            score = 6
        else:
            score = 4

        # 深刻度による調整
        severity_bonus = self.severity_mapping.get(severity, 0)
        score = max(score, severity_bonus)

        # 一般的な脆弱性タイプの場合はボーナス
        for cwe_id in cwe_info:
            if cwe_id in self.cwe_categories:
                score += 1
                break

        return min(score, 10)

    def _build_vulnerability_content(
        self,
        cve_id: str,
        description: str,
        cvss_score: float,
        cvss_vector: str,
        cwe_info: List[str],
        references: List[str],
        severity: str,
    ) -> str:
        """脆弱性記事の内容を構築"""
        content_parts = [
            f"脆弱性ID: {cve_id}",
            f"深刻度: {severity} (CVSS {cvss_score})",
            "",
            "概要:",
            description,
            "",
        ]

        if cwe_info:
            content_parts.extend(
                [
                    "脆弱性タイプ:",
                    ", ".join(
                        [
                            f"{cwe} ({self.cwe_categories.get(cwe, 'その他')})"
                            for cwe in cwe_info
                        ]
                    ),
                    "",
                ]
            )

        if cvss_vector:
            content_parts.extend([f"CVSSベクトル: {cvss_vector}", ""])

        if references:
            content_parts.extend(["参考リンク:", *[f"- {url}" for url in references], ""])

        content_parts.append(f"詳細情報: https://nvd.nist.gov/vuln/detail/{cve_id}")

        return "\n".join(content_parts)

    def get_remaining_requests(self) -> int:
        """残りリクエスト数を取得"""
        return max(0, self.daily_limit - self.request_count)

    def get_service_status(self) -> Dict[str, Any]:
        """サービス状況を取得"""
        return {
            "service": "nvd",
            "daily_limit": self.daily_limit,
            "requests_made": self.request_count,
            "remaining_requests": self.get_remaining_requests(),
            "cvss_threshold": self.cvss_threshold,
            "rate_limit_status": self.get_rate_limit_status(),
            "api_key_configured": bool(self.api_key),  # NVDはAPIキー不要だが統一性のため
        }
