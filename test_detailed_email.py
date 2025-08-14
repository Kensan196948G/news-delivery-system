#!/usr/bin/env python3
"""
詳細情報を含むテストメール生成
Test email with detailed article information
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from models.article import Article
from notifiers.gmail_sender import GmailSender
from utils.config import ConfigManager

def generate_test_articles():
    """各カテゴリに適切な数のテスト記事を生成"""
    articles = []
    
    # セキュリティ記事（20件必要）
    for i in range(25):  # 25件生成（表示は20件）
        articles.append(Article(
            url=f"https://security.example.com/news{i+1}",
            title=f"【セキュリティ】重大な脆弱性CVE-2025-{1000+i}が発見される",
            description=f"広く使用されているソフトウェアに深刻な脆弱性が発見されました。影響範囲は{random.choice(['広範', '中程度', '限定的'])}です。",
            content=f"セキュリティ研究者により、重要なソフトウェアコンポーネントに脆弱性が発見されました。この脆弱性を悪用されると、{random.choice(['リモートコード実行', '権限昇格', '情報漏洩'])}の可能性があります。",
            source_name=random.choice(["Security Alert", "CVE Database", "JPCERT/CC", "IPA"]),
            published_at=datetime.now() - timedelta(hours=random.randint(0, 48)),
            category="security",
            importance_score=random.randint(6, 10),
            keywords=["セキュリティ", "脆弱性", f"CVE-2025-{1000+i}", "緊急", "パッチ"],
            sentiment="negative",
            summary=f"CVE-2025-{1000+i}: 深刻度{random.choice(['Critical', 'High', 'Medium'])}の脆弱性。早急なパッチ適用が推奨されます。影響を受けるシステムは全体の約{random.randint(10, 80)}%と推定。"
        ))
    
    # 技術・AI記事（20件必要）
    for i in range(22):  # 22件生成（表示は20件）
        articles.append(Article(
            url=f"https://tech.example.com/ai{i+1}",
            title=f"【AI技術】{random.choice(['Google', 'Microsoft', 'OpenAI', 'Meta'])}が新たなAIモデルを発表",
            description=f"最新のAI技術により、{random.choice(['自然言語処理', '画像認識', '音声認識', '予測分析'])}の精度が大幅に向上",
            content="人工知能分野での新たなブレークスルーが達成されました。",
            source_name=random.choice(["TechCrunch", "Wired", "MIT Tech Review", "AI News"]),
            published_at=datetime.now() - timedelta(hours=random.randint(0, 72)),
            category="tech",
            importance_score=random.randint(5, 9),
            keywords=["AI", "機械学習", "ディープラーニング", "イノベーション", "技術革新"],
            sentiment="positive",
            summary=f"新しいAIモデルは従来比{random.randint(20, 150)}%の性能向上を実現。{random.choice(['企業向け', '研究用', '一般公開'])}として{random.choice(['今月', '来月', '年内'])}にリリース予定。"
        ))
    
    # 国際社会記事（15件必要）
    for i in range(18):  # 18件生成（表示は15件）
        articles.append(Article(
            url=f"https://world.example.com/social{i+1}",
            title=f"【国際】{random.choice(['国連', 'WHO', 'EU', 'ASEAN'])}が{random.choice(['人権', '難民', '気候変動', '教育'])}問題について声明",
            description="国際社会における重要な動きがありました",
            content="世界各国が協力して問題解決に取り組んでいます。",
            source_name=random.choice(["BBC", "CNN", "Reuters", "AP News"]),
            published_at=datetime.now() - timedelta(hours=random.randint(0, 96)),
            category="international_social",
            importance_score=random.randint(4, 8),
            keywords=["国際協力", "人権", "社会問題", "グローバル", "外交"],
            sentiment=random.choice(["positive", "neutral", "negative"]),
            summary=f"{random.choice(['先進国', '新興国', 'G7', 'G20'])}が中心となり、{random.choice(['2030年', '2025年', '今後5年'])}までに問題解決を目指す新たな枠組みが提案されました。"
        ))
    
    # 国際経済記事（15件必要）
    for i in range(17):  # 17件生成（表示は15件）
        articles.append(Article(
            url=f"https://economy.example.com/global{i+1}",
            title=f"【経済】{random.choice(['米国', '中国', 'EU', '日本'])}の{random.choice(['GDP', '失業率', 'インフレ率', '金利'])}が{random.choice(['上昇', '下落', '横ばい'])}",
            description="世界経済に影響を与える重要な経済指標が発表されました",
            content="市場関係者は今後の動向を注視しています。",
            source_name=random.choice(["Bloomberg", "Financial Times", "WSJ", "Economist"]),
            published_at=datetime.now() - timedelta(hours=random.randint(0, 48)),
            category="international_economy",
            importance_score=random.randint(5, 8),
            keywords=["経済", "市場", "金融", "投資", "為替"],
            sentiment=random.choice(["positive", "neutral", "negative"]),
            summary=f"市場アナリストは、この動きが{random.choice(['短期的', '中期的', '長期的'])}に{random.choice(['株式市場', '為替市場', '債券市場'])}に{random.choice(['大きな', '限定的な', '中程度の'])}影響を与えると予測。"
        ))
    
    # 国内経済記事（8件必要）
    for i in range(10):  # 10件生成（表示は8件）
        articles.append(Article(
            url=f"https://japan.example.com/economy{i+1}",
            title=f"【国内経済】{random.choice(['日銀', '財務省', '経産省'])}が{random.choice(['金融政策', '経済対策', '産業支援'])}を発表",
            description="日本経済に関する重要な政策が発表されました",
            content="国内経済の活性化に向けた新たな取り組みが始まります。",
            source_name=random.choice(["日経新聞", "読売新聞", "NHK", "共同通信"]),
            published_at=datetime.now() - timedelta(hours=random.randint(0, 24)),
            category="domestic_economy",
            importance_score=random.randint(4, 7),
            keywords=["日本経済", "政策", "金融", "産業", "成長戦略"],
            sentiment="neutral",
            summary=f"新政策により、{random.choice(['中小企業', '製造業', 'サービス業'])}への支援が強化。{random.choice(['今年度', '来年度', '3年間'])}で総額{random.randint(1, 10)}兆円規模の予算を投入予定。"
        ))
    
    # 国内社会記事（10件必要）
    for i in range(12):  # 12件生成（表示は10件）
        articles.append(Article(
            url=f"https://japan.example.com/social{i+1}",
            title=f"【国内】{random.choice(['厚労省', '文科省', '環境省'])}が{random.choice(['社会保障', '教育改革', '環境対策'])}の新方針を発表",
            description="日本社会に関する重要な政策が発表されました",
            content="国民生活に直結する新たな施策が始まります。",
            source_name=random.choice(["朝日新聞", "毎日新聞", "産経新聞", "東京新聞"]),
            published_at=datetime.now() - timedelta(hours=random.randint(0, 36)),
            category="domestic_social",
            importance_score=random.randint(3, 7),
            keywords=["社会", "政策", "福祉", "教育", "生活"],
            sentiment="neutral",
            summary=f"新制度は{random.choice(['4月', '10月', '来年'])}から開始。対象者は約{random.randint(100, 1000)}万人と推定され、{random.choice(['高齢者', '子育て世帯', '若者'])}への支援が拡充されます。"
        ))
    
    return articles

async def test_detailed_email():
    """詳細情報を含むテストメール送信"""
    
    print("=" * 60)
    print("  詳細記事情報テストメール")
    print("=" * 60)
    
    # テスト記事生成
    print("\n1. テスト記事を生成中...")
    articles = generate_test_articles()
    print(f"   生成された記事数: {len(articles)}件")
    
    # カテゴリ別集計
    categories_count = {
        'セキュリティ': len([a for a in articles if a.category == 'security']),
        '技術・AI': len([a for a in articles if a.category == 'tech']),
        '国際社会': len([a for a in articles if a.category == 'international_social']),
        '国際経済': len([a for a in articles if a.category == 'international_economy']),
        '国内経済': len([a for a in articles if a.category == 'domestic_economy']),
        '国内社会': len([a for a in articles if a.category == 'domestic_social']),
    }
    
    print("\n2. カテゴリ別記事数:")
    for cat, count in categories_count.items():
        print(f"   - {cat}: {count}件")
    
    try:
        # GmailSender初期化
        print("\n3. メール生成中...")
        sender = GmailSender()
        
        # プレーンテキストメール生成（内部メソッドを直接呼び出し）
        now = datetime.now()
        text_content = sender._generate_text_email(
            articles=articles,
            delivery_time=now,
            delivery_name="テスト配信",
            delivery_icon="🧪",
            delivery_time_str=now.strftime('%H:%M')
        )
        
        # ファイルに保存
        output_file = Path("test_detailed_email_output.txt")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("詳細記事情報を含むテストメール\n")
            f.write(f"生成時刻: {now.strftime('%Y年%m月%d日 %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            f.write(text_content)
        
        print(f"\n✅ メール内容を生成しました")
        print(f"   保存先: {output_file}")
        
        # 実際の送信も試みる
        print("\n4. 実際のメール送信を試行中...")
        result = await sender.send_daily_report(
            articles=articles,
            pdf_path=None
        )
        
        if result:
            print("   ✅ メール送信成功！")
        else:
            print("   ⚠️ メール送信はスキップされました")
            
    except Exception as e:
        print(f"\n❌ エラー: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("  テスト完了")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_detailed_email())