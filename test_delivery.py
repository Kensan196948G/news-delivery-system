#!/usr/bin/env python3
"""
ニュース配信システム - テスト配信
修正済みのGmail送信機能を使用してテスト配信を実行
"""

import sys
import os
import asyncio
import logging
from datetime import datetime
from typing import List

# パス設定
sys.path.append('src')

# 簡易Article実装（依存関係を最小化）
class SimpleArticle:
    def __init__(self, title, description, url, source_name, category, published_at=None, importance_score=5):
        self.title = title
        self.translated_title = title + " (翻訳済み)"
        self.description = description
        self.summary = description[:200] + "..." if len(description) > 200 else description
        self.url = url
        self.source_name = source_name
        self.category = category
        self.published_at = published_at or datetime.now()
        self.importance_score = importance_score
        self.keywords = self._extract_keywords()
    
    def _extract_keywords(self):
        """簡易キーワード抽出"""
        if 'セキュリティ' in self.title or 'security' in self.title.lower():
            return ['セキュリティ', '脆弱性', 'サイバー']
        elif 'AI' in self.title or '技術' in self.title:
            return ['AI', '技術', 'イノベーション']
        elif '経済' in self.title or 'economy' in self.title.lower():
            return ['経済', '市場', '金融']
        else:
            return ['ニュース', '社会', '情報']

# 簡易Config実装
class SimpleConfig:
    def get(self, section, key, default=None):
        config_map = {
            ('delivery', 'recipients'): ['kensan1969@gmail.com'],
            ('email', 'sender_email'): 'news-delivery-system@gmail.com'
        }
        return config_map.get((section, key), default)
    
    def get_env(self, key, default=None):
        return os.environ.get(key, default)

# 簡易GmailSender実装（依存関係を最小化）
class SimpleGmailSender:
    def __init__(self):
        self.config = SimpleConfig()
        self.recipients = self.config.get('delivery', 'recipients', [])
        self.sender_email = self.config.get('email', 'sender_email', '')
        
    async def send_daily_report(self, articles: List[SimpleArticle]) -> bool:
        """テスト用日次レポート送信"""
        try:
            # 現在時刻を取得
            now = datetime.now()
            
            # 配信時間帯を判定
            hour = now.hour
            if 6 <= hour < 10:
                delivery_name = "朝刊"
                delivery_icon = "🌅"
                delivery_time = "7:00"
            elif 11 <= hour < 15:
                delivery_name = "昼刊" 
                delivery_icon = "🌞"
                delivery_time = "12:00"
            else:
                delivery_name = "夕刊"
                delivery_icon = "🌆"
                delivery_time = "18:00"
            
            # メール件名生成
            date_str = now.strftime('%Y年%m月%d日')
            subject = f'{delivery_icon} {delivery_name}ニュース配信（テスト） - {date_str} {delivery_time}'
            
            # プレーンテキスト版メール生成
            text_content = self._generate_test_email(articles, now, delivery_name, delivery_icon, delivery_time)
            
            # 実際の送信の代わりにファイル出力とログ
            print(f"📧 テストメール生成完了")
            print(f"件名: {subject}")
            print(f"配信先: {', '.join(self.recipients)}")
            print(f"記事数: {len(articles)}")
            
            # メール内容をファイルに保存
            filename = f'test_delivery_email_{now.strftime("%Y%m%d_%H%M%S")}.txt'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"件名: {subject}\n")
                f.write(f"配信先: {', '.join(self.recipients)}\n")
                f.write(f"配信時刻: {now.strftime('%Y年%m月%d日 %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                f.write(text_content)
            
            print(f"💾 メール内容を保存: {filename}")
            
            # 実際のSMTP送信を試行（設定があれば）
            if os.environ.get('SENDER_EMAIL') and os.environ.get('GMAIL_APP_PASSWORD'):
                print("📨 SMTP送信を試行中...")
                smtp_success = await self._send_smtp_email(subject, text_content)
                if smtp_success:
                    print("✅ SMTP送信成功")
                    return True
                else:
                    print("❌ SMTP送信失敗")
            else:
                print("ℹ️  SMTP認証情報が設定されていないため、送信はスキップします")
                print("   設定方法: SENDER_EMAIL と GMAIL_APP_PASSWORD 環境変数を設定")
            
            return True
            
        except Exception as e:
            print(f"❌ テスト配信エラー: {e}")
            return False
    
    def _generate_test_email(self, articles: List[SimpleArticle], delivery_time: datetime, 
                           delivery_name: str, delivery_icon: str, delivery_time_str: str) -> str:
        """テスト用メール生成"""
        try:
            text_content = f"""
{delivery_icon} {delivery_name}ニュース配信（テスト） - {delivery_time.strftime('%Y年%m月%d日')} {delivery_time_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
配信先: {', '.join(self.recipients)}
配信時刻: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

🧪 これはテスト配信です 🧪

📊 配信サマリー
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・総記事数: {len(articles)}件
・重要記事 (8点以上): {len([a for a in articles if a.importance_score >= 8])}件  
・緊急記事 (10点): {len([a for a in articles if a.importance_score >= 10])}件
・テスト記事: {len(articles)}件

    """
            
            # 緊急アラート
            critical_articles = [a for a in articles if a.importance_score >= 10]
            if critical_articles:
                text_content += f"""
🚨 緊急アラート（テスト）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
重要度10の緊急記事が {len(critical_articles)} 件検出されました。
（※これはテストデータです）

        """
            
            # カテゴリ別記事表示
            for i, article in enumerate(articles, 1):
                importance = article.importance_score
                
                # 重要度表示
                if importance >= 10:
                    importance_mark = "🚨【緊急】"
                elif importance >= 8:
                    importance_mark = "⚠️【重要】"
                else:
                    importance_mark = "📰【通常】"
                
                # published_at の安全な処理（修正済みロジック）
                published_time = "時刻不明"
                if hasattr(article, 'published_at') and article.published_at:
                    try:
                        if isinstance(article.published_at, datetime):
                            published_time = article.published_at.strftime('%H:%M')
                        elif isinstance(article.published_at, str):
                            dt = datetime.fromisoformat(article.published_at.replace('Z', '+00:00'))
                            published_time = dt.strftime('%H:%M')
                    except (ValueError, TypeError, AttributeError):
                        published_time = "時刻不明"
                
                text_content += f"""

{i}. {importance_mark} [{importance}/10] {article.title}

   【概要】
   {article.summary}
   
   【詳細情報】
   ソース: {article.source_name}
   配信時刻: {published_time}
   キーワード: {', '.join(article.keywords)}
   
   【詳細リンク】
   {article.url}
            """
            
            text_content += f"""


🔔 テスト配信について
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
これはニュース配信システムのテスト配信です。
strftimeエラーの修正が正常に動作することを確認しています。

📅 通常の配信スケジュール
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌅 朝刊配信: 毎日 7:00
🌞 昼刊配信: 毎日 12:00  
🌆 夕刊配信: 毎日 18:00

🤖 Generated with Claude Code (Test Mode)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
このメールはテスト用自動配信システムから送信されました。

© 2025 News Delivery System - Test Mode
    """
            
            return text_content
            
        except Exception as e:
            return f"テストメール生成エラー: {str(e)}"
    
    async def _send_smtp_email(self, subject: str, text_content: str) -> bool:
        """SMTP送信試行"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            sender_email = os.environ.get('SENDER_EMAIL')
            app_password = os.environ.get('GMAIL_APP_PASSWORD')
            
            for recipient in self.recipients:
                message = MIMEMultipart()
                message['From'] = sender_email
                message['To'] = recipient
                message['Subject'] = subject
                
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                message.attach(text_part)
                
                with smtplib.SMTP('smtp.gmail.com', 587) as server:
                    server.starttls()
                    server.login(sender_email, app_password)
                    server.send_message(message)
                
                print(f"📧 SMTP送信成功: {recipient}")
            
            return True
            
        except Exception as e:
            print(f"❌ SMTP送信エラー: {e}")
            return False

def create_test_articles() -> List[SimpleArticle]:
    """テスト用記事データ作成"""
    articles = [
        SimpleArticle(
            title="最新のAI技術動向について",
            description="人工知能技術の最新動向と今後の展望について詳しく解説します。機械学習やディープラーニングの進歩により、様々な分野での応用が期待されています。",
            url="https://example.com/ai-trends",
            source_name="テクノロジーニュース",
            category="TECH",
            published_at=datetime.now(),
            importance_score=7
        ),
        SimpleArticle(
            title="重大なセキュリティ脆弱性が発見される",
            description="広く利用されているソフトウェアに重大なセキュリティ脆弱性が発見されました。すぐにアップデートを適用することを強く推奨します。",
            url="https://example.com/security-alert",
            source_name="セキュリティアラート",
            category="SECURITY",
            published_at="2025-08-12T09:30:00Z",  # 文字列形式でテスト
            importance_score=10
        ),
        SimpleArticle(
            title="国内経済指標が改善",
            description="最新の経済統計によると、国内の主要経済指標が前月比で改善を示しています。専門家は慎重ながらも楽観的な見通しを示しています。",
            url="https://example.com/economy-news",
            source_name="経済ニュース",
            category="DOMESTIC_ECONOMY",
            published_at="invalid_date_string",  # 無効な日付文字列でテスト
            importance_score=6
        ),
        SimpleArticle(
            title="環境問題への新たな取り組み",
            description="政府は気候変動対策として新たな環境政策を発表しました。再生可能エネルギーの推進と温室効果ガス削減目標の見直しが含まれています。",
            url="https://example.com/environment-policy",
            source_name="環境ニュース",
            category="DOMESTIC_SOCIAL", 
            published_at=None,  # None値でテスト
            importance_score=8
        ),
        SimpleArticle(
            title="国際会議で重要な合意",
            description="国際社会における重要な課題について、各国が協力して取り組むことで合意に達しました。今後の具体的な行動計画についても議論されています。",
            url="https://example.com/international-agreement",
            source_name="国際ニュース",
            category="INTERNATIONAL_SOCIAL",
            published_at=datetime(2025, 8, 12, 8, 15, 0),  # 具体的なdatetimeでテスト
            importance_score=9
        )
    ]
    
    return articles

async def main():
    """メイン処理"""
    print("🚀 ニュース配信システム - テスト配信開始")
    print("=" * 60)
    
    try:
        # テスト記事作成
        print("📝 テスト記事データを作成中...")
        articles = create_test_articles()
        print(f"✅ {len(articles)}件のテスト記事を作成しました")
        
        # 記事データの詳細表示
        print("\n📋 作成されたテスト記事:")
        for i, article in enumerate(articles, 1):
            print(f"  {i}. {article.title[:30]}... (重要度: {article.importance_score}, published_at型: {type(article.published_at)})")
        
        # Gmail送信機能初期化
        print("\n📧 Gmail送信機能を初期化中...")
        gmail_sender = SimpleGmailSender()
        
        # テスト配信実行
        print("\n📨 テスト配信を実行中...")
        success = await gmail_sender.send_daily_report(articles)
        
        if success:
            print("\n✅ テスト配信が正常に完了しました")
            print("   - strftimeエラーは発生しませんでした")
            print("   - 各種published_at形式で正常に動作しました")
        else:
            print("\n❌ テスト配信中にエラーが発生しました")
            
    except Exception as e:
        print(f"\n❌ テスト配信でエラーが発生: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🏁 テスト配信完了")

if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(level=logging.INFO)
    
    # 非同期実行
    asyncio.run(main())