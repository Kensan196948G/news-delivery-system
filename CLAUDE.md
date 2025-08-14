ニュース自動配信システム構築仕様書
1. プロジェクト概要
1.1 プロジェクト名
ニュース自動配信システム（News Delivery System）

1.2 目的
Claude Codeおよび各種APIを活用して、複数のニュースソースから最新情報を自動収集・翻訳・分析し、定期的にHTML/PDF形式でレポートを生成してGmail配信するシステムを構築する。

1.3 背景
複数のニュースソースから関心のある情報を効率的に収集したい

海外ニュースは日本語に翻訳して読みたい

重要な情報を見逃さないよう、定期的に配信を受けたい

ITシステム運用管理者として、セキュリティ脆弱性情報を迅速に把握したい

1.4 ステークホルダー
利用者: システム管理者、エンドユーザー

CTO(CEO): プロジェクト全体の戦略決定・最終承認・リソース配分

プロジェクトマネージャー: 進捗管理・品質管理・チーム調整・スケジュール管理

開発チーム:
- 主任開発者（Developer 1）: アーキテクチャ設計・コードレビュー・技術選定
- バックエンド開発者（Developer 2）: API連携・データベース設計・サーバーサイド実装
- フロントエンド開発者（Developer 3）: UI/UX・レポート生成・メール配信機能
- インフラ開発者（Developer 4）: 環境構築・デプロイメント・監視・セキュリティ

運用者: システム保守・監視・トラブルシューティング

1.5 開発体制とチーム構成
1.5.1 組織構成
```
CTO(CEO)
   │
   └── プロジェクトマネージャー
       │
       ├── 主任開発者（Developer 1）
       ├── バックエンド開発者（Developer 2）
       ├── フロントエンド開発者（Developer 3）
       └── インフラ開発者（Developer 4）
```

1.5.2 役割と責任
CTO(CEO):
- プロジェクト全体の戦略方針決定
- 予算承認・リソース配分
- 最終的な品質承認
- ステークホルダーとの調整

プロジェクトマネージャー:
- 日次・週次進捗管理
- タスク優先順位付け
- 品質ゲート管理
- リスク管理・課題解決
- チーム間調整・コミュニケーション

主任開発者（Developer 1）:
- システムアーキテクチャ設計
- 技術選定・技術標準策定
- コードレビュー統括
- チーム内技術指導

バックエンド開発者（Developer 2）:
- API連携機能実装
- データベース設計・実装
- バッチ処理システム実装
- パフォーマンス最適化

フロントエンド開発者（Developer 3）:
- レポート生成機能実装
- HTMLテンプレート設計
- メール配信機能実装
- ユーザビリティ改善

インフラ開発者（Developer 4）:
- 開発・本番環境構築
- CI/CDパイプライン構築
- セキュリティ対策実装
- 監視・アラート設定

1.5.3 コミュニケーション体制
定例会議:
- 日次スタンドアップ（15分）: 進捗共有・課題報告
- 週次レビュー（60分）: 週間振り返り・次週計画
- スプリントプランニング（120分）: 2週間スプリント計画
- 月次ステアリング（90分）: CTO向け進捗報告

コミュニケーションツール:
- チャット: Slack/Teams（日常コミュニケーション）
- タスク管理: Jira/Trello（進捗可視化）
- ドキュメント共有: Confluence/SharePoint
- コードレビュー: GitHub Pull Request

1.5.4 承認フロー
技術仕様:
主任開発者 → プロジェクトマネージャー → CTO

実装完了:
担当開発者 → 主任開発者（コードレビュー） → プロジェクトマネージャー（品質確認）

リリース判定:
プロジェクトマネージャー → CTO（最終承認）

2. 機能要件
2.1 ニュース収集機能
2.1.1 収集対象カテゴリ
国内社会ニュース

ソース: 国内主要メディア

言語: 日本語

収集件数: 1回あたり10件程度

国際社会ニュース

ソース: 海外主要メディア

言語: 英語（その他言語含む）

収集件数: 1回あたり15件程度

特記事項: 人権関連ニュースを優先

IT/AIニュース

ソース: 技術系メディア、ブログ

言語: 英語/日本語

収集件数: 1回あたり20件程度

サイバーセキュリティニュース

ソース: セキュリティ専門サイト、CVEデータベース

言語: 英語/日本語

収集件数: 1回あたり20件程度

特記事項: 脆弱性情報（CVE）を含む

2.1.2 使用API
NewsAPI（一般ニュース）

GNews API（補助的使用）

NVD API（脆弱性情報）

その他必要に応じて追加

2.2 翻訳機能
2.2.1 翻訳対象
海外ニュースのタイトルと本文

セキュリティアラートの詳細

2.2.2 翻訳仕様
使用API: DeepL API

対応言語: 英語→日本語（主要）、その他言語→日本語

翻訳品質: 高精度モード使用

2.3 分析・要約機能
2.3.1 Claude API連携
記事の重要度評価（1-10スケール）

200-250文字での要約生成

キーワード抽出（5個）

カテゴリ自動分類

センチメント分析

2.3.2 Claude Code活用
複雑な分析タスクの自動化

カスタム処理ロジックの実装

エラーハンドリングの最適化

ワークフロー全体の制御

2.4 レポート生成機能
2.4.1 レポート形式
HTML形式（メール本文用）

PDF形式（添付ファイル用）

2.4.2 レポート構成
ヘッダー部

配信日時

総記事数

重要度サマリー

本文部

カテゴリ別セクション

各記事の表示項目：翻訳済みタイトル

要約（200-250文字）

重要度スコア

キーワードタグ

元記事へのリンク

配信元

公開日時

緊急アラート部

CVSS 9.0以上の脆弱性

重要度10の記事

2.5 配信機能
2.5.1 配信方法
主要: Gmail（HTMLメール + PDF添付）

補助: ショートメッセージ（重要アラートのみ）

2.5.2 配信スケジュール
定期配信: 1日3回（7:00、12:00、18:00）Windowsタスクスケジューラで自動実行

緊急配信: 重要度10またはCVSS 9.0以上検出時

2.5.3 配信先管理
配信先メールアドレスの登録

配信停止機能

配信履歴の保存

3. 非機能要件
3.1 性能要件
ニュース収集処理: 5分以内で完了

レポート生成: 2分以内で完了

全体処理時間: 10分以内

3.2 可用性要件
システム稼働率: 95%以上

自動リトライ機能: 最大3回

エラー時の通知機能

3.3 セキュリティ要件
APIキーの暗号化保存

環境変数による機密情報管理

HTTPSによる通信

アクセスログの記録

3.4 運用性要件
シンプルなPython実行環境

ログローテーション機能

バックアップ機能（外付けHDD内での世代管理）

基本的なエラー監視

3.5 拡張性要件
ニュースソースの追加が容易

新しい言語への対応が可能

配信先の追加が簡単

外付けHDDの容量に応じたデータ保存

4. システムアーキテクチャ
4.1 全体構成図
┌─────────────────────────────────────────────────────────────┐
│                    Windows PC (ローカル環境)                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐                                              │
│  │   タスク     │  ← 7:00, 12:00, 18:00に起動                 │
│  │スケジューラ  │                                              │
│  └──────┬──────┘                                              │
│         ↓                                                      │
│  ┌─────────────────────────────┐                             │
│  │    main.py (メインプロセス)   │                             │
│  ├─────────────────────────────┤                             │
│  │ 1. ニュース収集              │ → NewsAPI, NVD API          │
│  │ 2. 翻訳処理                 │ → DeepL API                  │
│  │ 3. AI分析・要約             │ → Claude API                 │
│  │ 4. レポート生成             │                              │
│  │ 5. メール配信               │ → Gmail API                  │
│  └─────────────────────────────┘                             │
│         ↓                                                      │
│  ┌─────────────────────────────┐                             │
│  │   外付けHDD (3TB)            │                             │
│  │   E:\NewsDeliverySystem\     │                             │
│  └─────────────────────────────┘                             │
└─────────────────────────────────────────────────────────────┘

4.2 ディレクトリ構造
C:\NewsDeliverySystem\              # プログラム本体
├── src\                           # ソースコード
│   ├── main.py                   # メインプログラム
│   ├── collectors\               # ニュース収集モジュール
│   │   ├── __init__.py
│   │   ├── base_collector.py
│   │   ├── newsapi_collector.py
│   │   ├── nvd_collector.py
│   │   └── gnews_collector.py
│   ├── processors\               # 処理モジュール
│   │   ├── __init__.py
│   │   ├── translator.py        # DeepL翻訳
│   │   ├── analyzer.py          # Claude分析
│   │   └── deduplicator.py      # 重複除去
│   ├── generators\               # レポート生成
│   │   ├── __init__.py
│   │   ├── html_generator.py
│   │   └── pdf_generator.py
│   ├── notifiers\                # 配信モジュール
│   │   ├── __init__.py
│   │   └── gmail_sender.py
│   ├── utils\                    # ユーティリティ
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── logger.py
│   │   └── cache_manager.py
│   └── models\                   # データモデル
│       ├── __init__.py
│       └── article.py
├── config\                        # 設定ファイル
│   ├── config.json
│   └── .env
├── templates\                     # HTMLテンプレート
│   └── email_template.html
├── scripts\                       # スクリプト
│   ├── setup.py                  # 初期設定
│   └── create_task.ps1           # タスク登録
├── requirements.txt              # 依存パッケージ
└── README.md                     # 説明書

E:\NewsDeliverySystem\              # データ保存先（外付けHDD）
├── articles\                      # 記事データ
│   └── 2024\
│       └── 06\
│           └── 27\
│               ├── raw\          # 原文
│               └── processed\    # 処理済み
├── reports\                       # レポート
│   ├── daily\
│   │   └── 2024\
│   │       └── 06\
│   │           └── 27\
│   └── monthly\
├── database\                      # SQLiteDB
│   └── news.db
├── cache\                         # キャッシュ
│   ├── api_cache\
│   └── dedup_cache\
├── logs\                          # ログ
│   └── 2024\
│       └── 06\
└── backup\                        # バックアップ

5. モジュール設計
5.1 メインモジュール (main.py)
"""
メインプログラム
実行フロー制御とエラーハンドリング
"""
import asyncio
import sys
from datetime import datetime
from utils.config import Config
from utils.logger import Logger

class NewsDeliverySystem:
    def __init__(self):
        self.config = Config()
        self.logger = Logger(__name__)
        
    async def run(self):
        """メイン処理フロー"""
        try:
            # 1. ニュース収集
            articles = await self.collect_news()
            
            # 2. 重複除去
            unique_articles = await self.deduplicate(articles)
            
            # 3. 翻訳処理
            translated_articles = await self.translate(unique_articles)
            
            # 4. AI分析・要約
            analyzed_articles = await self.analyze(translated_articles)
            
            # 5. レポート生成
            report_paths = await self.generate_reports(analyzed_articles)
            
            # 6. メール配信
            await self.send_notifications(report_paths, analyzed_articles)
            
            # 7. データ保存
            await self.save_data(analyzed_articles)
            
        except Exception as e:
            self.logger.error(f"System error: {str(e)}")
            await self.send_error_notification(e)

5.2 ニュース収集モジュール
5.2.1 基底クラス (base_collector.py)
from abc import ABC, abstractmethod
from typing import List, Dict
import aiohttp
from utils.cache_manager import CacheManager

class BaseCollector(ABC):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.cache = CacheManager()
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
        
    @abstractmethod
    async def collect(self, category: str, count: int) -> List[Dict]:
        """ニュース収集の実装"""
        pass
        
    async def fetch_with_cache(self, url: str, params: Dict) -> Dict:
        """キャッシュ付きHTTPリクエスト"""
        cache_key = f"{url}:{str(params)}"
        cached = self.cache.get(cache_key)
        
        if cached:
            return cached
            
        async with self.session.get(url, params=params) as response:
            data = await response.json()
            self.cache.set(cache_key, data, expire=3600)  # 1時間キャッシュ
            return data

5.2.2 NewsAPI収集 (newsapi_collector.py)
class NewsAPICollector(BaseCollector):
    BASE_URL = "https://newsapi.org/v2"
    
    async def collect(self, category: str, count: int) -> List[Dict]:
        """NewsAPIからニュース収集"""
        endpoint = self._get_endpoint(category)
        params = self._build_params(category, count)
        
        data = await self.fetch_with_cache(
            f"{self.BASE_URL}/{endpoint}",
            params
        )
        
        return self._parse_articles(data)
        
    def _get_endpoint(self, category: str) -> str:
        """カテゴリに応じたエンドポイント選択"""
        if category in ['domestic_social', 'domestic_economy']:
            return 'top-headlines'
        return 'everything'
        
    def _build_params(self, category: str, count: int) -> Dict:
        """APIパラメータ構築"""
        params = {
            'apiKey': self.api_key,
            'pageSize': count
        }
        
        # カテゴリ別パラメータ
        category_params = {
            'domestic_social': {
                'country': 'jp',
                'category': 'general'
            },
            'international_social': {
                'q': 'human rights OR social justice OR migration',
                'language': 'en',
                'sortBy': 'relevancy'
            },
            'domestic_economy': {
                'country': 'jp',
                'category': 'business'
            },
            'international_economy': {
                'q': 'economy OR market OR trade OR inflation',
                'language': 'en',
                'sortBy': 'popularity'
            },
            'tech': {
                'q': 'artificial intelligence OR machine learning OR cloud computing',
                'language': 'en',
                'sortBy': 'publishedAt'
            },
            'security': {
                'q': 'cybersecurity OR vulnerability OR ransomware OR data breach',
                'language': 'en',
                'sortBy': 'relevancy'
            }
        }
        
        params.update(category_params.get(category, {}))
        return params

5.3 翻訳モジュール (translator.py)
class DeepLTranslator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api-free.deepl.com/v2/translate"
        self.cache = CacheManager()
        
    async def translate_batch(self, articles: List[Article]) -> List[Article]:
        """記事のバッチ翻訳"""
        tasks = []
        for article in articles:
            if self._needs_translation(article):
                tasks.append(self.translate_article(article))
            else:
                tasks.append(asyncio.create_task(self._return_as_is(article)))
                
        return await asyncio.gather(*tasks)
        
    async def translate_article(self, article: Article) -> Article:
        """単一記事の翻訳"""
        # キャッシュチェック
        cache_key = f"translate:{article.url}"
        cached = self.cache.get(cache_key)
        if cached:
            article.translated_title = cached['title']
            article.translated_content = cached['content']
            return article
            
        # 翻訳実行
        texts = [article.title, article.description or article.content]
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url,
                headers={'Authorization': f'DeepL-Auth-Key {self.api_key}'},
                data={
                    'text': texts,
                    'source_lang': 'EN',
                    'target_lang': 'JA'
                }
            ) as response:
                result = await response.json()
                
        translations = result['translations']
        article.translated_title = translations[0]['text']
        article.translated_content = translations[1]['text']
        
        # キャッシュ保存
        self.cache.set(cache_key, {
            'title': article.translated_title,
            'content': article.translated_content
        }, expire=86400)  # 24時間
        
        return article

5.4 AI分析モジュール (analyzer.py)
import anthropic
from typing import List, Dict
import json

class ClaudeAnalyzer:
    def __init__(self, api_key: str):
        self.client = anthropic.Client(api_key=api_key)
        self.cache = CacheManager()
        
    async def analyze_batch(self, articles: List[Article]) -> List[Article]:
        """記事のバッチ分析"""
        # 重要度で優先順位付け
        priority_articles = self._prioritize_articles(articles)
        
        tasks = []
        for article in priority_articles[:20]:  # 上位20件のみClaude分析
            tasks.append(self.analyze_article(article))
            
        # 残りは簡易分析
        for article in priority_articles[20:]:
            tasks.append(self._simple_analyze(article))
            
        return await asyncio.gather(*tasks)
        
    async def analyze_article(self, article: Article) -> Article:
        """Claude APIによる詳細分析"""
        # キャッシュチェック
        cache_key = f"analyze:{article.url}"
        cached = self.cache.get(cache_key)
        if cached:
            return self._apply_analysis(article, cached)
            
        prompt = f"""
以下のニュース記事を分析してください。

タイトル: {article.translated_title or article.title}
内容: {article.translated_content or article.content}

以下のJSON形式で回答してください:
{{
    "summary": "200-250文字の要約",
    "importance_score": 1-10の重要度,
    "keywords": ["キーワード1", "キーワード2", "キーワード3", "キーワード4", "キーワード5"],
    "category": "社会/経済/IT/セキュリティ",
    "sentiment": "positive/neutral/negative",
    "key_points": ["ポイント1", "ポイント2", "ポイント3"]
}}
"""
        
        try:
            response = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # JSON解析
            content = response.content[0].text
            analysis = json.loads(self._extract_json(content))
            
            # キャッシュ保存
            self.cache.set(cache_key, analysis, expire=86400*7)  # 7日間
            
            return self._apply_analysis(article, analysis)
            
        except Exception as e:
            self.logger.error(f"Claude analysis error: {str(e)}")
            return self._simple_analyze(article)
            
    def _extract_json(self, text: str) -> str:
        """テキストからJSON部分を抽出"""
        import re
        match = re.search(r'\{[\s\S]*\}', text)
        return match.group() if match else '{}'

5.5 レポート生成モジュール
5.5.1 HTML生成 (html_generator.py)
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import os

class HTMLReportGenerator:
    def __init__(self, template_dir: str):
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.template = self.env.get_template('email_template.html')
        
    def generate(self, articles: List[Article], date: datetime) -> str:
        """HTMLレポート生成"""
        # カテゴリ別に整理
        categorized = self._categorize_articles(articles)
        
        # 統計情報生成
        stats = self._generate_statistics(articles)
        
        # 緊急アラート抽出
        alerts = self._extract_alerts(articles)
        
        # テンプレートレンダリング
        html = self.template.render(
            date=date.strftime('%Y年%m月%d日 %A'),
            total_articles=len(articles),
            categories=categorized,
            statistics=stats,
            alerts=alerts,
            generated_at=datetime.now()
        )
        
        return html
        
    def _categorize_articles(self, articles: List[Article]) -> Dict:
        """カテゴリ別に記事を整理"""
        categories = {
            '国内社会': [],
            '国際社会': [],
            '国内経済': [],
            '国際経済': [],
            'IT/AI': [],
            'セキュリティ': []
        }
        
        for article in articles:
            category = self._map_category(article)
            if category in categories:
                categories[category].append(article)
                
        # 各カテゴリ内で重要度順にソート
        for category in categories:
            categories[category].sort(
                key=lambda x: x.importance_score or 5,
                reverse=True
            )
            
        return categories

5.5.2 PDF生成 (pdf_generator.py)
import pdfkit
from typing import Optional
import os

class PDFReportGenerator:
    def __init__(self):
        self.options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None,
            'enable-local-file-access': None
        }
        
    def generate_from_html(self, html: str, output_path: str) -> bool:
        """HTMLからPDF生成"""
        try:
            # wkhtmltopdfのパス設定（Windows）
            config = pdfkit.configuration(
                wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
            )
            
            # PDF生成
            pdfkit.from_string(
                html,
                output_path,
                options=self.options,
                configuration=config
            )
            
            return os.path.exists(output_path)
            
        except Exception as e:
            self.logger.error(f"PDF generation error: {str(e)}")
            return False

5.6 Gmail配信モジュール (gmail_sender.py)
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import base64
import os

class GmailSender:
    def __init__(self, credentials_path: str):
        self.creds = self._load_credentials(credentials_path)
        self.service = build('gmail', 'v1', credentials=self.creds)
        
    async def send_report(
        self,
        recipient: str,
        subject: str,
        html_content: str,
        pdf_path: Optional[str] = None
    ):
        """レポートメール送信"""
        try:
            message = MIMEMultipart()
            message['to'] = recipient
            message['subject'] = subject
            
            # HTML本文
            html_part = MIMEText(html_content, 'html')
            message.attach(html_part)
            
            # PDF添付
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as f:
                    attach = MIMEBase('application', 'pdf')
                    attach.set_payload(f.read())
                    encoders.encode_base64(attach)
                    attach.add_header(
                        'Content-Disposition',
                        f'attachment; filename={os.path.basename(pdf_path)}'
                    )
                    message.attach(attach)
                    
            # エンコードして送信
            raw = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            body = {'raw': raw}
            
            result = await asyncio.to_thread(
                self.service.users().messages().send(
                    userId='me',
                    body=body
                ).execute
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Gmail send error: {str(e)}")
            raise

6. データ設計
6.1 SQLiteデータベース設計
6.1.1 テーブル定義
-- 記事テーブル
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    url_hash TEXT NOT NULL,
    title TEXT NOT NULL,
    translated_title TEXT,
    description TEXT,
    content TEXT,
    translated_content TEXT,
    summary TEXT,
    source_name TEXT,
    author TEXT,
    published_at DATETIME,
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    category TEXT,
    importance_score INTEGER DEFAULT 5,
    keywords TEXT,  -- JSON配列
    sentiment TEXT,
    processed BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_published_at ON articles(published_at);
CREATE INDEX idx_category ON articles(category);
CREATE INDEX idx_importance ON articles(importance_score);
CREATE INDEX idx_url_hash ON articles(url_hash);

-- 配信履歴テーブル
CREATE TABLE delivery_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    delivery_type TEXT NOT NULL,  -- 'scheduled', 'urgent'
    recipient_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    article_count INTEGER,
    categories TEXT,  -- JSON
    status TEXT NOT NULL,  -- 'sent', 'failed'
    error_message TEXT,
    html_path TEXT,
    pdf_path TEXT,
    delivered_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- API使用履歴
CREATE TABLE api_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_name TEXT NOT NULL,
    endpoint TEXT,
    request_count INTEGER DEFAULT 1,
    response_status INTEGER,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- キャッシュテーブル
CREATE TABLE cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    expire_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

6.2 ファイル保存形式
6.2.1 記事データ (JSON形式)
{
    "article_id": "20240627_123456",
    "url": "https://example.com/news/article",
    "title": "Original Title",
    "translated_title": "翻訳されたタイトル",
    "description": "Article description",
    "content": "Full article content",
    "translated_content": "翻訳された本文",
    "summary": "200-250文字の要約",
    "source": {
        "id": "bbc-news",
        "name": "BBC News"
    },
    "author": "John Doe",
    "published_at": "2024-06-27T10:30:00Z",
    "collected_at": "2024-06-27T12:00:00Z",
    "category": "international_social",
    "analysis": {
        "importance_score": 8,
        "keywords": ["keyword1", "keyword2", "keyword3"],
        "sentiment": "neutral",
        "key_points": ["point1", "point2", "point3"]
    },
    "metadata": {
        "translation_method": "deepl",
        "analysis_method": "claude",
        "processing_time": 2.5
    }
}

7. 設定情報
7.1 config.json
{
    "system": {
        "version": "1.0.0",
        "timezone": "Asia/Tokyo",
        "language": "ja"
    },
    "paths": {
        "data_root": "E:\\NewsDeliverySystem",
        "templates": "C:\\NewsDeliverySystem\\templates",
        "logs": "E:\\NewsDeliverySystem\\logs"
    },
    "collection": {
        "categories": {
            "domestic_social": {
                "enabled": true,
                "count": 10,
                "priority": 1
            },
            "international_social": {
                "enabled": true,
                "count": 15,
                "priority": 2,
                "keywords": ["human rights", "social justice", "migration"]
            },
            "domestic_economy": {
                "enabled": true,
                "count": 8,
                "priority": 3
            },
            "international_economy": {
                "enabled": true,
                "count": 15,
                "priority": 4
            },
            "tech": {
                "enabled": true,
                "count": 20,
                "priority": 5
            },
            "security": {
                "enabled": true,
                "count": 20,
                "priority": 6,
                "alert_threshold": 9.0
            }
        }
    },
    "delivery": {
        "recipients": ["user@example.com"],
        "schedule": ["07:00", "12:00", "18:00"],
        "urgent_notification": {
            "enabled": true,
            "importance_threshold": 10,
            "cvss_threshold": 9.0
        }
    },
    "api_limits": {
        "newsapi": {
            "daily_limit": 1000,
            "rate_limit": 500
        },
        "deepl": {
            "monthly_limit": 500000,
            "batch_size": 50
        },
        "claude": {
            "daily_limit": 1000,
            "concurrent": 5
        }
    },
    "cache": {
        "api_cache_ttl": 3600,
        "article_cache_ttl": 86400,
        "analysis_cache_ttl": 604800
    },
    "logging": {
        "level": "INFO",
        "max_file_size": "10MB",
        "backup_count": 5
    }
}

7.2 環境変数 (.env)
# API Keys
NEWSAPI_KEY=your_newsapi_key_here
DEEPL_API_KEY=your_deepl_api_key_here
ANTHROPIC_API_KEY=your_claude_api_key_here
GNEWS_API_KEY=your_gnews_api_key_here

# Gmail OAuth
GMAIL_CREDENTIALS_PATH=C:\NewsDeliverySystem\config\gmail_credentials.json
GMAIL_TOKEN_PATH=C:\NewsDeliverySystem\config\gmail_token.json

# Database
DB_PATH=E:\NewsDeliverySystem\database\news.db

# System
DEBUG=False
LOG_LEVEL=INFO

7.3 システム設定
配信設定

配信時刻（7:00、12:00、18:00）

配信先メールアドレス

送信元メールアドレス（Gmailアカウント）

メール件名フォーマット

収集設定

各カテゴリの収集件数

優先キーワードリスト

除外キーワードリスト

言語設定

8. エラー処理設計
8.1 エラー分類と対処
エラー種別例

対処方法

リトライ

API制限エラー (429 Too Many Requests)

待機後リトライ

3回

ネットワークエラー (ConnectionError)

即座にリトライ

3回

認証エラー (401 Unauthorized)

エラー通知

なし

データ形式エラー (JSON Parse Error)

ログ記録、スキップ

なし

ディスク容量エラー (No space left)

緊急通知

なし

8.2 エラー通知
class ErrorNotifier:
    async def notify_critical_error(self, error: Exception):
        """重大エラーの通知"""
        subject = f"[緊急] ニュース配信システムエラー: {error.__class__.__name__}"
        content = f"""
        エラーが発生しました:
        
        種別: {error.__class__.__name__}
        メッセージ: {str(error)}
        発生時刻: {datetime.now()}
        
        詳細はログファイルを確認してください。
        """
        
        # Gmail送信
        await self.gmail_sender.send_error_notification(
            self.config.get('admin_email'),
            subject,
            content
        )

9. ログ設計
9.1 ログレベル
ERROR: システムエラー、API失敗

WARNING: リトライ発生、容量警告

INFO: 正常処理、統計情報

DEBUG: 詳細な処理情報

9.2 ログフォーマット
[2024-06-27 12:00:00,123] [INFO] [main.NewsDeliverySystem] Starting news collection process
[2024-06-27 12:00:05,456] [INFO] [collectors.NewsAPICollector] Collected 10 articles from domestic_social
[2024-06-27 12:00:10,789] [WARNING] [processors.DeepLTranslator] Rate limit approaching: 450000/500000 characters used
[2024-06-27 12:00:15,012] [ERROR] [notifiers.GmailSender] Failed to send email: [Errno 11001] getaddrinfo failed

10. パフォーマンス設計
10.1 並行処理
ニュース収集: 最大6並行（カテゴリ別）

翻訳処理: バッチ50件、最大3並行

AI分析: 最大5並行

10.2 キャッシュ戦略
APIレスポンス: 1時間

翻訳結果: 24時間

分析結果: 7日間

重複チェック: 30日間

10.3 リソース制限
メモリ使用: 最大2GB

ディスク使用: 警告閾値80%

API呼び出し: レート制限の80%で警告

11. セキュリティ設計
11.1 認証情報管理
APIキー: 環境変数で管理

Gmail認証: OAuthトークン使用

ファイルアクセス: 読み取り専用

11.2 データ保護
個人情報: 配信先メールアドレスのみ

ログ: 個人情報をマスク

バックアップ: ローカルのみ

12. 環境構築と前提条件
12.1 Windows環境
OS情報: Windows 10/11

ハードウェア情報: CPU/メモリ容量、外付けHDD (3TB) の接続と空き容量、ネットワーク接続の安定性

12.2 Python環境
Pythonインストール: Python 3.11以降のインストール

仮想環境の作成:

cd C:\NewsDeliverySystem
python -m venv venv
venv\Scripts\activate

pip最新版へのアップデート

必要なパッケージ:

aiohttp==3.9.0
anthropic==0.18.0
google-auth==2.23.0
google-auth-oauthlib==1.1.0
google-api-python-client==2.100.0
jinja2==3.1.2
pdfkit==1.0.0
python-dotenv==1.0.0
requests==2.31.0
sqlite3（標準ライブラリ）

12.3 追加ソフトウェア
wkhtmltopdf（PDF生成用）:

インストールパス: C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe にインストールされていること。

12.4 タスクスケジューラ設定
タスク登録スクリプト (create_task.ps1):

# ニュース配信タスクの作成
$taskName = "NewsDeliverySystem"
$taskPath = "C:\NewsDeliverySystem\src\main.py"
$pythonPath = "C:\Python311\python.exe" # Pythonのインストールパスに合わせて変更

# 7:00のタスク
$trigger1 = New-ScheduledTaskTrigger -Daily -At 7:00AM
# 12:00のタスク
$trigger2 = New-ScheduledTaskTrigger -Daily -At 12:00PM
# 18:00のタスク
$trigger3 = New-ScheduledTaskTrigger -Daily -At 6:00PM

$action = New-ScheduledTaskAction -Execute $pythonPath -Argument $taskPath
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask `
    -TaskName $taskName `
    -Trigger $trigger1,$trigger2,$trigger3 `
    -Action $action `
    -Principal $principal `
    -Settings $settings `
    -Description "ニュース自動配信システム"

Windowsタスクスケジューラへのアクセス権限があること。

12.5 ディレクトリ構成とパーミッション
プログラム配置: プロジェクトルート: C:\NewsDeliverySystem\

データ保存先: E:\NewsDeliverySystem\

フォルダ作成とパーミッション:

# プログラム本体のディレクトリ作成
mkdir -p C:\NewsDeliverySystem\{src,config,templates,scripts}

# データ保存先のディレクトリ作成
mkdir -p E:\NewsDeliverySystem\{articles,reports,database,cache,logs,backup}

# 必要に応じてパーミッション設定（Windowsでは通常不要だが、共有フォルダなどの場合は設定）

13. API関連情報
13.1 NewsAPI
アカウント作成URL: https://newsapi.org/register

プラン選択: 無料プランの制限確認

APIキーの取得

利用制限の確認: 無料プラン: 1日1,000リクエスト、レート制限: なし、商用利用: 不可、データ保持: 制限あり

13.2 DeepL API
アカウント作成URL: https://www.deepl.com/pro-api

無料プラン登録

APIキーの取得

利用制限の確認: 無料プラン: 月500,000文字、対応言語リスト、バッチ翻訳の制限

13.3 Claude API (Anthropic)
アカウント作成URL: https://www.anthropic.com

APIキーの取得

利用プラン選択

利用制限の確認: トークン制限、レート制限、料金体系の理解

13.4 Gmail API
Google Cloud Console設定: プロジェクト作成、Gmail API有効化、OAuth 2.0クライアントID作成

認証情報: クライアントID、クライアントシークレット、リダイレクトURI設定、スコープ設定（gmail.send）

13.5 NVD API（オプション）
API情報URL: https://nvd.nist.gov/developers

APIキー申請（推奨）

レート制限の確認

14. 実装に必要な詳細情報
14.1 ニュースカテゴリ詳細
国内社会ニュース: 対象メディア指定、優先トピック、除外条件

国際社会ニュース: 人権関連キーワード（英語）、対象国・地域、信頼できるソース

経済ニュース: 重要指標キーワード、市場情報の範囲、専門用語の扱い

IT/AIニュース: 技術キーワードリスト、優先度の高いトピック、技術レベル設定

セキュリティニュース: CVSSスコア閾値、対象製品・ベンダー、緊急度の判定基準

14.2 翻訳設定
翻訳対象: タイトルの最大文字数、本文の最大文字数、専門用語辞書

翻訳品質: フォーマリティレベル、用語の一貫性設定、固有名詞の扱い

14.3 AI分析設定
要約設定: 要約文字数（200-250文字）、要約スタイル、含めるべき要素

重要度: 評価基準の詳細

15. 制約事項
15.1 API制限
NewsAPI: 1日1,000リクエスト（無料プラン）

DeepL API: 月500,000文字（無料プラン）

Claude API: プランに応じた制限

Gmail API: 1日250クォータユニット

15.2 技術的制約
Claude Code実行環境の制限

ローカルマシンのリソース制限

ネットワーク帯域の考慮

外付けHDDの読み書き速度

15.3 運用制約
個人プロジェクトとしての運用

24時間365日の監視は不要

コスト最小化の必要性

16. 成果物
16.1 ソフトウェア成果物
ソースコード一式: Pythonスクリプト、Dockerファイル（※要件定義にはないが、詳細設計で言及されている場合は考慮）、設定ファイル

ドキュメント: システム設計書、API仕様書、運用手順書、トラブルシューティングガイド

設定テンプレート: config.json（設定ファイル）、環境変数テンプレート（.env.example）、タスクスケジューラ設定（XML形式）

16.2 運用成果物
日次配信レポート（HTML/PDF）

月次統計レポート

エラーログ

17. プロジェクトスケジュール
17.1 開発フェーズ（6週間 - 2週間スプリント × 3回）

Sprint 1（第1-2週）: 基盤構築・環境準備
担当: 全チーム
- CTO: プロジェクト戦略承認・リソース確保
- PM: スプリント計画・タスク分解・進捗管理
- 主任開発者: アーキテクチャ設計・技術選定
- バックエンド開発者: 開発環境構築・データベース設計
- フロントエンド開発者: UIフレームワーク選定・テンプレート設計
- インフラ開発者: 開発環境構築・CI/CD基盤準備

Sprint 2（第3-4週）: コア機能実装
担当: 開発チーム中心
- PM: 品質ゲート管理・課題解決・チーム調整
- 主任開発者: コードレビュー・技術指導
- バックエンド開発者: ニュース収集API実装・翻訳機能実装
- フロントエンド開発者: レポート生成機能実装
- インフラ開発者: セキュリティ実装・監視設定

Sprint 3（第5-6週）: 統合・配信・テスト
担当: 全チーム
- CTO: 品質承認・リリース判定
- PM: 統合テスト管理・リリース準備
- 主任開発者: 統合テスト・パフォーマンス最適化
- バックエンド開発者: AI分析機能実装・パフォーマンス調整
- フロントエンド開発者: メール配信機能実装・ユーザビリティ改善
- インフラ開発者: 本番環境構築・デプロイメント準備

17.2 スプリント詳細スケジュール

Sprint 1 詳細:
Week 1-2:
- Day 1-2: プロジェクトキックオフ・要件確認（全チーム）
- Day 3-5: アーキテクチャ設計・技術選定（主任開発者）
- Day 6-10: 開発環境構築・データベース設計（バックエンド・インフラ）

Sprint 2 詳細:
Week 3-4:
- Day 11-15: ニュース収集API実装（バックエンド開発者）
- Day 11-15: HTMLテンプレート実装（フロントエンド開発者）
- Day 16-20: 翻訳機能実装・レポート生成（バックエンド・フロントエンド）

Sprint 3 詳細:
Week 5-6:
- Day 21-25: AI分析機能・メール配信実装（バックエンド・フロントエンド）
- Day 26-30: 統合テスト・デプロイメント・品質確認（全チーム）

17.3 運用フェーズ
初期運用期間: 2週間（調整期間）
- PM: 運用監視・課題対応
- インフラ開発者: システム監視・パフォーマンス調整

本格運用: 継続的
- 運用者: 日常保守・監視
- 月次レビュー: CTO・PM・主任開発者

18. リスクと対策
18.1 技術的リスク
リスク影響度

発生確率

対策

API制限超過

高

キャッシュ活用、レート制限実装

翻訳品質不足

中

複数翻訳APIの併用検討

システム障害

高

自動リトライ、エラー通知

18.2 運用リスク
リスク影響度

発生確率

対策

コスト超過

中

使用量モニタリング、アラート設定

メンテナンス負荷

中

自動化の徹底、ログ分析

19. 成功基準
19.1 定量的基準
日次配信成功率: 95%以上

記事収集数: 1日あたり50件以上

処理時間: 10分以内

API使用量: 制限内での運用

19.2 定性的基準
重要なニュースの見逃しがない

翻訳品質が実用レベル

レポートの可読性が高い

運用負荷が最小限

20. 承認事項
20.1 前提条件の確認
組織的な開発体制での運用

CTO・PM・4名の開発者体制が確保されていること

APIキーの取得が完了していること

開発環境（Windows/Linux）でPython実行環境が利用可能であること

外付けHDD（3TB）またはクラウドストレージが確保されていること

必要な権限（タスクスケジューラ、システム設定）が確保されていること

コミュニケーションツール（Slack/Teams、Jira/Trello等）が利用可能であること

20.2 変更管理・承認プロセス
要件変更: プロジェクトマネージャー → CTO承認

技術仕様変更: 主任開発者 → PM → CTO承認

大規模変更時: 影響分析実施・ステークホルダー合意

緊急対応: PM判断（事後CTO報告）

20.3 品質管理
コードレビュー: 主任開発者による必須レビュー

テスト: 各スプリント終了時の品質ゲート

リリース承認: CTO最終承認

作成日: 2024年XX月XX日
作成者: [作成者名]
バージョン: 1.0
次回レビュー予定: 運用開始2週間後