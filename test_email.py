#!/usr/bin/env python3
"""
テストメール送信スクリプト
Test email sending functionality
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from models.article import Article
from notifiers.gmail_sender import GmailSender
from utils.config import ConfigManager

async def test_email_with_sample_articles():
    """サンプル記事を使用したテストメール送信"""
    
    print("=" * 50)
    print("テストメール送信開始")
    print("=" * 50)
    
    # サンプル記事の作成
    sample_articles = [
        Article(
            url="https://example.com/news1",
            title="【テスト】AI技術の最新動向について",
            description="人工知能技術の進化と今後の展望",
            content="AIの進化により、様々な分野で革新が起きています。",
            source_name="Tech News",
            published_at=datetime.now(),
            category="tech",
            importance_score=8,
            keywords=["AI", "機械学習", "技術革新"],
            sentiment="positive",
            summary="AI技術が急速に発展し、社会に大きな影響を与えています。"
        ),
        Article(
            url="https://example.com/news2",
            title="【テスト】サイバーセキュリティ緊急アラート",
            description="新たな脆弱性が発見されました",
            content="重要なセキュリティアップデートが必要です。",
            source_name="Security Alert",
            published_at=datetime.now(),
            category="security",
            importance_score=10,
            keywords=["セキュリティ", "脆弱性", "緊急"],
            sentiment="negative",
            summary="緊急のセキュリティパッチが必要な脆弱性が発見されました。"
        ),
        Article(
            url="https://example.com/news3",
            title="【テスト】経済市場の動向分析",
            description="今週の市場動向レポート",
            content="株式市場は安定した推移を見せています。",
            source_name="Economic Times",
            published_at=datetime.now(),
            category="economy",
            importance_score=6,
            keywords=["経済", "市場", "投資"],
            sentiment="neutral",
            summary="市場は比較的安定した動きを見せており、投資家は慎重な姿勢を維持しています。"
        )
    ]
    
    try:
        # GmailSender初期化
        print("\n1. GmailSenderを初期化中...")
        sender = GmailSender()
        
        # 設定確認
        config = ConfigManager()
        recipients = config.get('delivery', 'recipients', default=['kensan1969@gmail.com'])
        print(f"   送信先: {recipients}")
        
        # テストメール送信（記事付き）
        print("\n2. サンプル記事付きテストメール送信中...")
        result = await sender.send_daily_report(
            articles=sample_articles,
            pdf_path=None  # PDFなし
        )
        
        if result:
            print("   ✅ テストメール送信成功！")
        else:
            print("   ❌ テストメール送信失敗")
            
        # シンプルなテストメール送信
        print("\n3. シンプルなテストメール送信中...")
        test_result = await sender.send_test_email(recipients)
        
        if test_result['success']:
            print("   ✅ シンプルテストメール送信成功！")
        else:
            print(f"   ❌ シンプルテストメール送信失敗: {test_result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("テスト完了")
    print("=" * 50)

async def test_simple_email():
    """最もシンプルなテストメール送信"""
    print("\nシンプルテストメール送信...")
    
    try:
        from notifiers.simple_gmail_sender import SimpleGmailSender
        
        # SimpleGmailSenderを使用
        sender = SimpleGmailSender()
        success = await sender.send_simple_test()
        
        if success:
            print("✅ SimpleGmailSender: テストメール送信成功")
        else:
            print("❌ SimpleGmailSender: テストメール送信失敗")
            
    except (ImportError, ValueError) as e:
        print(f"SimpleGmailSenderが使用できません: {e}")
        print("GmailSenderを使用します。")
        
        sender = GmailSender()
        result = await sender.send_test_email(['kensan1969@gmail.com'])
        
        if result['success']:
            print("✅ GmailSender: テストメール送信成功")
        else:
            print(f"❌ GmailSender: テストメール送信失敗 - {result.get('error')}")

async def main():
    """メイン実行関数"""
    print("\n" + "="*60)
    print("  ニュース配信システム - メール送信テスト")
    print("="*60)
    print(f"\n実行時刻: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
    
    # 環境変数の確認
    print("\n[環境変数チェック]")
    env_vars = ['GMAIL_CREDENTIALS_PATH', 'GMAIL_TOKEN_PATH', 'SENDER_EMAIL']
    
    for var in env_vars:
        value = os.getenv(var, 'Not set')
        if value != 'Not set':
            print(f"  ✓ {var}: 設定済み")
        else:
            print(f"  ✗ {var}: 未設定")
    
    # メニュー表示
    print("\n[テストメニュー]")
    print("1. サンプル記事付きテストメール")
    print("2. シンプルなテストメール")
    print("3. 両方実行")
    print("0. 終了")
    
    choice = input("\n選択してください (0-3): ").strip()
    
    if choice == '1':
        await test_email_with_sample_articles()
    elif choice == '2':
        await test_simple_email()
    elif choice == '3':
        await test_email_with_sample_articles()
        await test_simple_email()
    elif choice == '0':
        print("終了します。")
    else:
        print("無効な選択です。デフォルトで両方実行します。")
        await test_email_with_sample_articles()
        await test_simple_email()

if __name__ == "__main__":
    # イベントループ実行
    asyncio.run(main())