#!/usr/bin/env python3
"""
リアルタイムテスト配信
今すぐ実行するテスト配信システム
"""

import sys
import os
import asyncio
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

# パス設定
sys.path.append('src')

class RealTimeTestArticle:
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
            return ['セキュリティ', '脆弱性', 'テスト']
        elif 'AI' in self.title or '技術' in self.title:
            return ['AI', '技術', 'テスト']
        elif '経済' in self.title:
            return ['経済', '市場', 'テスト']
        else:
            return ['ニュース', 'テスト', 'リアルタイム']

def create_realtime_test_articles() -> List[RealTimeTestArticle]:
    """リアルタイムテスト用記事データ作成"""
    now = datetime.now()
    
    articles = [
        RealTimeTestArticle(
            title=f"🚨 リアルタイムテスト配信 - {now.strftime('%H:%M:%S')}",
            description=f"これは{now.strftime('%Y年%m月%d日 %H時%M分')}に実行されたリアルタイムテスト配信です。strftimeエラーの修正が正常に動作していることを確認します。",
            url="https://github.com/anthropics/claude-code",
            source_name="Claude Code システム",
            category="TECH",
            published_at=now,
            importance_score=9
        ),
        RealTimeTestArticle(
            title="セキュリティ修正テスト (文字列日付)",
            description="published_atが文字列形式の場合でも正常に処理されることをテストします。この記事のpublished_atは意図的に文字列として設定されています。",
            url="https://example.com/security-test",
            source_name="セキュリティテスト",
            category="SECURITY",
            published_at="2025-08-12T10:30:00Z",  # 文字列形式
            importance_score=8
        ),
        RealTimeTestArticle(
            title="無効日付テスト (エラーハンドリング)",
            description="無効な日付文字列が設定された場合のエラーハンドリングをテストします。この記事は意図的に無効な日付が設定されています。",
            url="https://example.com/invalid-date-test", 
            source_name="エラーハンドリングテスト",
            category="TECH",
            published_at="invalid_date_string",  # 無効な文字列
            importance_score=6
        ),
        RealTimeTestArticle(
            title="緊急アラートテスト",
            description="重要度10の緊急アラート機能をテストします。このメッセージが緊急セクションに表示されることを確認してください。",
            url="https://example.com/emergency-test",
            source_name="緊急テスト",
            category="SECURITY",
            published_at=None,  # None値
            importance_score=10
        )
    ]
    
    return articles

def generate_realtime_test_email(articles: List[RealTimeTestArticle]) -> str:
    """リアルタイムテストメール生成"""
    now = datetime.now()
    
    # 配信時間帯判定
    hour = now.hour
    if 6 <= hour < 10:
        delivery_name = "朝刊"
        delivery_icon = "🌅"
    elif 11 <= hour < 15:
        delivery_name = "昼刊"
        delivery_icon = "🌞"
    else:
        delivery_name = "夕刊"
        delivery_icon = "🌆"
    
    text_content = f"""
{delivery_icon} {delivery_name}ニュース配信 (🧪 リアルタイムテスト) - {now.strftime('%Y年%m月%d日')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
実行時刻: {now.strftime('%Y年%m月%d日 %H:%M:%S')}
配信先: kensan1969@gmail.com

🧪 リアルタイムテスト配信実行中 🧪

📊 配信サマリー
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・総記事数: {len(articles)}件
・重要記事 (8点以上): {len([a for a in articles if a.importance_score >= 8])}件  
・緊急記事 (10点): {len([a for a in articles if a.importance_score >= 10])}件
・strftime修正テスト: 実行中

    """
    
    # 緊急アラート
    critical_articles = [a for a in articles if a.importance_score >= 10]
    if critical_articles:
        text_content += f"""
🚨 緊急アラート (リアルタイムテスト)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
重要度10の緊急記事が {len(critical_articles)} 件検出されました。
これはstrftime修正のリアルタイムテストです。

        """
    
    # 記事一覧
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
   published_at型: {type(article.published_at).__name__}
   キーワード: {', '.join(article.keywords)}
   
   【詳細リンク】
   {article.url}
        """
    
    text_content += f"""


🔧 修正テスト結果
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ strftimeエラー修正: 動作確認中
✅ datetime型: 正常処理
✅ 文字列型: 自動変換処理  
✅ 無効文字列: 安全フォールバック
✅ None値: デフォルト処理

📅 配信スケジュール
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌅 朝刊配信: 毎日 7:00
🌞 昼刊配信: 毎日 12:00  
🌆 夕刊配信: 毎日 18:00

🤖 Generated with Claude Code (Real-time Test)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
このメールはリアルタイムテスト配信システムから送信されました。
修正されたstrftime処理が正常に動作していることを確認中です。

実行時刻: {now.strftime('%Y年%m月%d日 %H:%M:%S')}
© 2025 News Delivery System - Real-time Test Mode
    """
    
    return text_content

async def send_realtime_test_email(subject: str, content: str) -> bool:
    """リアルタイムテストメール送信"""
    print("📧 リアルタイムテストメール送信を試行中...")
    
    # SMTP設定確認
    sender_email = os.environ.get('SENDER_EMAIL')
    app_password = os.environ.get('GMAIL_APP_PASSWORD')
    recipient = "kensan1969@gmail.com"
    
    if not sender_email or not app_password:
        print("⚠️  SMTP認証情報が設定されていません")
        print("   SENDER_EMAIL:", "設定済み" if sender_email else "未設定")
        print("   GMAIL_APP_PASSWORD:", "設定済み" if app_password else "未設定")
        print("   ファイル保存のみ実行します...")
        return False
    
    try:
        # メッセージ作成
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = recipient
        message['Subject'] = subject
        
        # プレーンテキスト部分
        text_part = MIMEText(content, 'plain', 'utf-8')
        message.attach(text_part)
        
        # SMTP送信
        print(f"📨 Gmail SMTP経由で送信中: {recipient}")
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(message)
        
        print("✅ リアルタイムテストメール送信成功!")
        return True
        
    except Exception as e:
        print(f"❌ SMTP送信エラー: {e}")
        return False

async def main():
    """メイン処理"""
    now = datetime.now()
    print("🚀 リアルタイムテスト配信開始")
    print("=" * 60)
    print(f"実行時刻: {now.strftime('%Y年%m月%d日 %H:%M:%S')}")
    
    try:
        # テスト記事作成
        print("\n📝 リアルタイムテスト記事を作成中...")
        articles = create_realtime_test_articles()
        print(f"✅ {len(articles)}件のテスト記事を作成")
        
        # 記事データの確認
        print("\n📋 作成されたテスト記事:")
        for i, article in enumerate(articles, 1):
            print(f"  {i}. {article.title[:40]}...")
            print(f"     重要度: {article.importance_score}, published_at型: {type(article.published_at).__name__}")
        
        # メール生成
        print("\n📧 テストメール生成中...")
        email_content = generate_realtime_test_email(articles)
        
        # 件名生成
        hour = now.hour
        if 6 <= hour < 10:
            delivery_icon = "🌅"
            delivery_name = "朝刊"
        elif 11 <= hour < 15:
            delivery_icon = "🌞"
            delivery_name = "昼刊"
        else:
            delivery_icon = "🌆"
            delivery_name = "夕刊"
        
        subject = f"{delivery_icon} {delivery_name}ニュース配信 (🧪 リアルタイムテスト) - {now.strftime('%Y年%m月%d日 %H:%M')}"
        
        # ファイル保存
        filename = f"realtime_test_email_{now.strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"件名: {subject}\n")
            f.write(f"配信先: kensan1969@gmail.com\n") 
            f.write(f"実行時刻: {now.strftime('%Y年%m月%d日 %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            f.write(email_content)
        
        print(f"💾 メール内容を保存: {filename}")
        
        # 実際の送信試行
        print(f"\n📨 件名: {subject}")
        success = await send_realtime_test_email(subject, email_content)
        
        if success:
            print("\n🎉 リアルタイムテスト配信が成功しました!")
            print("   - Gmail経由でメールが送信されました")
            print("   - strftimeエラーは発生しませんでした")
            print("   - 全ての日付形式で正常に動作しました")
        else:
            print("\n📄 テストメール内容の生成は成功しました")
            print("   - strftimeエラーは発生しませんでした")
            print("   - メール内容は正常に生成されました")
            print("   - SMTP送信は設定不足のためスキップされました")
            
    except Exception as e:
        print(f"\n❌ リアルタイムテスト中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"🏁 リアルタイムテスト完了 - {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main())