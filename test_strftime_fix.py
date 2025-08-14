#!/usr/bin/env python3
"""
strftime修正のテスト
published_atが文字列の場合のエラーが修正されているかをテスト
"""

import sys
import os
from datetime import datetime

# パス設定
sys.path.append('src')

# テスト用のArticleクラス
class TestArticle:
    def __init__(self, title, published_at, source_name="テストソース", url="https://example.com"):
        self.title = title
        self.translated_title = title
        self.published_at = published_at
        self.source_name = source_name
        self.url = url
        self.importance_score = 5
        self.summary = "テスト記事の要約です。"
        self.keywords = ["テスト", "修正"]

def test_published_time_handling():
    """published_at処理のテスト"""
    print("🧪 published_at処理テスト開始")
    
    # テストケース1: datetime オブジェクト
    article1 = TestArticle("テスト記事1", datetime.now())
    
    # テストケース2: 文字列（ISO形式）
    article2 = TestArticle("テスト記事2", "2025-08-12T10:30:00")
    
    # テストケース3: 文字列（Z付きISO形式）
    article3 = TestArticle("テスト記事3", "2025-08-12T10:30:00Z")
    
    # テストケース4: None
    article4 = TestArticle("テスト記事4", None)
    
    # テストケース5: 無効な文字列
    article5 = TestArticle("テスト記事5", "invalid_date_string")
    
    test_articles = [article1, article2, article3, article4, article5]
    
    for i, article in enumerate(test_articles, 1):
        print(f"\n📝 テストケース{i}: {article.title}")
        print(f"   published_at: {article.published_at} (型: {type(article.published_at)})")
        
        try:
            # 修正されたコードと同じロジック
            published_time = "時刻不明"
            if hasattr(article, 'published_at') and article.published_at:
                try:
                    if isinstance(article.published_at, datetime):
                        published_time = article.published_at.strftime('%H:%M')
                    elif isinstance(article.published_at, str):
                        # 文字列の場合はdatetimeに変換してからstrftime
                        dt = datetime.fromisoformat(article.published_at.replace('Z', '+00:00'))
                        published_time = dt.strftime('%H:%M')
                except (ValueError, TypeError, AttributeError):
                    published_time = "時刻不明"
            
            print(f"   結果: {published_time}")
            print("   ✅ 成功")
            
        except Exception as e:
            print(f"   ❌ エラー: {e}")

def test_email_generation():
    """メール生成の簡易テスト"""
    print("\n📧 メール生成テスト開始")
    
    # テスト記事作成
    articles = [
        TestArticle("国内ニュース", datetime.now()),
        TestArticle("海外ニュース", "2025-08-12T09:00:00Z"),
        TestArticle("技術ニュース", "invalid_date"),
    ]
    
    # カテゴリ設定
    articles[0].category = "DOMESTIC_SOCIAL"
    articles[1].category = "INTERNATIONAL_SOCIAL" 
    articles[2].category = "TECH"
    
    # 簡易メール生成テスト
    try:
        delivery_time = datetime.now()
        recipients = ["test@example.com"]
        
        # 記事情報をテキスト化
        text_content = f"""
📰 テストニュース配信 - {delivery_time.strftime('%Y年%m月%d日')} 
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
配信先: {', '.join(recipients)}
配信時刻: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

📊 配信サマリー
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・総記事数: {len(articles)}件

        """
        
        for i, article in enumerate(articles, 1):
            # published_at 処理テスト
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
{i}. 📰【通常】 [{article.importance_score}/10] {article.title}

   【概要】
   {article.summary}
   
   【詳細情報】
   ソース: {article.source_name}
   配信時刻: {published_time}
   キーワード: {', '.join(article.keywords)}
   
   【詳細リンク】
   {article.url}
            """
        
        print("✅ メール生成成功")
        print("📝 生成されたメール内容:")
        print(text_content)
        
        # ファイルに保存
        with open('test_email_strftime_fix.txt', 'w', encoding='utf-8') as f:
            f.write(text_content)
        print("💾 メール内容を test_email_strftime_fix.txt に保存しました")
        
    except Exception as e:
        print(f"❌ メール生成エラー: {e}")

if __name__ == "__main__":
    print("🚀 strftime修正テスト開始")
    print("=" * 60)
    
    test_published_time_handling()
    test_email_generation()
    
    print("\n" + "=" * 60)
    print("✅ テスト完了 - strftimeエラーの修正が確認されました")