"""
Simple Translator - 基本的な翻訳補助機能
DeepL APIが利用できない場合の代替翻訳サポート
"""

import re
from typing import Dict, Optional

class SimpleTranslator:
    """簡易翻訳・日本語化補助クラス"""
    
    # よく使われる英語フレーズの日本語変換辞書
    COMMON_PHRASES = {
        # ニュース関連
        'Breaking News': '速報',
        'Latest News': '最新ニュース',
        'Update': '更新情報',
        'Report': 'レポート',
        'Analysis': '分析',
        'Opinion': '意見',
        'Editorial': '社説',
        'Exclusive': '独占',
        'Investigation': '調査',
        'Review': 'レビュー',
        
        # 時間関連
        'Today': '本日',
        'Yesterday': '昨日',
        'Tomorrow': '明日',
        'This week': '今週',
        'Last week': '先週',
        'This month': '今月',
        'Last month': '先月',
        'hours ago': '時間前',
        'minutes ago': '分前',
        'Just now': 'たった今',
        
        # 重要度・緊急度
        'Urgent': '緊急',
        'Important': '重要',
        'Critical': '危機的',
        'Warning': '警告',
        'Alert': 'アラート',
        'Emergency': '緊急事態',
        'High priority': '高優先度',
        'Low priority': '低優先度',
        
        # 経済・ビジネス
        'Economy': '経済',
        'Market': '市場',
        'Stock': '株式',
        'Trade': '貿易',
        'Business': 'ビジネス',
        'Finance': '金融',
        'Investment': '投資',
        'Growth': '成長',
        'Decline': '下落',
        'Recession': '景気後退',
        'Inflation': 'インフレ',
        'Interest rate': '金利',
        'Exchange rate': '為替レート',
        'GDP': 'GDP（国内総生産）',
        
        # 政治・社会
        'Government': '政府',
        'Politics': '政治',
        'Election': '選挙',
        'Policy': '政策',
        'Law': '法律',
        'Court': '裁判所',
        'Parliament': '議会',
        'Democracy': '民主主義',
        'Human rights': '人権',
        'Social justice': '社会正義',
        'Migration': '移住・移民',
        'Refugee': '難民',
        'Climate change': '気候変動',
        'Global warming': '地球温暖化',
        
        # テクノロジー
        'Technology': 'テクノロジー',
        'AI': 'AI（人工知能）',
        'Artificial Intelligence': '人工知能',
        'Machine Learning': '機械学習',
        'Cloud Computing': 'クラウドコンピューティング',
        'Data Science': 'データサイエンス',
        'Blockchain': 'ブロックチェーン',
        'Cryptocurrency': '暗号通貨',
        'Cybersecurity': 'サイバーセキュリティ',
        'Digital': 'デジタル',
        'Internet': 'インターネット',
        'Software': 'ソフトウェア',
        'Hardware': 'ハードウェア',
        
        # セキュリティ
        'Security': 'セキュリティ',
        'Vulnerability': '脆弱性',
        'Threat': '脅威',
        'Attack': '攻撃',
        'Breach': '侵害',
        'Hack': 'ハッキング',
        'Malware': 'マルウェア',
        'Ransomware': 'ランサムウェア',
        'Phishing': 'フィッシング',
        'Data breach': 'データ侵害',
        'Privacy': 'プライバシー',
        
        # 地域・国
        'United States': 'アメリカ',
        'US': '米国',
        'UK': '英国',
        'United Kingdom': 'イギリス',
        'China': '中国',
        'Japan': '日本',
        'Europe': 'ヨーロッパ',
        'Asia': 'アジア',
        'Middle East': '中東',
        'Africa': 'アフリカ',
        'Latin America': 'ラテンアメリカ',
        'Global': 'グローバル',
        'International': '国際',
        'World': '世界',
        
        # 動作・状態
        'increase': '増加',
        'decrease': '減少',
        'rise': '上昇',
        'fall': '下落',
        'improve': '改善',
        'worsen': '悪化',
        'expand': '拡大',
        'contract': '縮小',
        'develop': '開発',
        'launch': '開始',
        'announce': '発表',
        'release': 'リリース',
        'update': '更新',
        'confirm': '確認',
        'deny': '否定',
    }
    
    @classmethod
    def translate_text(cls, text: str, max_length: int = 200) -> str:
        """
        テキストの簡易翻訳・日本語化
        
        Args:
            text: 元のテキスト
            max_length: 最大文字数
            
        Returns:
            日本語化されたテキスト
        """
        if not text:
            return ""
        
        result = text
        
        # よく使われるフレーズを置換（大文字小文字を無視）
        for eng, jpn in cls.COMMON_PHRASES.items():
            # 単語境界を考慮した置換
            pattern = r'\b' + re.escape(eng) + r'\b'
            result = re.sub(pattern, jpn, result, flags=re.IGNORECASE)
        
        # 数値の後の単位を日本語化
        result = re.sub(r'(\d+)\s*billion', r'\1億', result)
        result = re.sub(r'(\d+)\s*million', r'\1百万', result)
        result = re.sub(r'(\d+)\s*thousand', r'\1千', result)
        result = re.sub(r'(\d+)%', r'\1％', result)
        result = re.sub(r'\$(\d+)', r'\1ドル', result)
        
        # 月名を日本語化
        months = {
            'January': '1月', 'February': '2月', 'March': '3月',
            'April': '4月', 'May': '5月', 'June': '6月',
            'July': '7月', 'August': '8月', 'September': '9月',
            'October': '10月', 'November': '11月', 'December': '12月'
        }
        for eng, jpn in months.items():
            result = re.sub(eng, jpn, result, flags=re.IGNORECASE)
        
        # 曜日を日本語化
        weekdays = {
            'Monday': '月曜日', 'Tuesday': '火曜日', 'Wednesday': '水曜日',
            'Thursday': '木曜日', 'Friday': '金曜日', 
            'Saturday': '土曜日', 'Sunday': '日曜日'
        }
        for eng, jpn in weekdays.items():
            result = re.sub(eng, jpn, result, flags=re.IGNORECASE)
        
        # 長すぎる場合は切り詰め
        if len(result) > max_length:
            result = result[:max_length] + "..."
        
        # まだ大部分が英語の場合でも、可能な限り日本語化を試みる
        if cls._is_mostly_english(result):
            # 基本的な文構造の日本語化
            result = cls._convert_to_japanese_structure(result, max_length)
        
        return result
    
    @classmethod
    def _is_mostly_english(cls, text: str) -> bool:
        """テキストが主に英語かどうかを判定"""
        if not text:
            return False
        
        # アルファベットの比率を計算
        alpha_chars = sum(1 for c in text if c.isalpha() and ord(c) < 128)
        total_chars = sum(1 for c in text if c.isalpha())
        
        if total_chars == 0:
            return False
        
        # 70%以上がアルファベットなら英語と判定
        return (alpha_chars / total_chars) > 0.7
    
    @classmethod
    def _convert_to_japanese_structure(cls, text: str, max_length: int = 200) -> str:
        """英語文を日本語的な構造に変換"""
        # 最も重要な単語を抽出して日本語化
        important_words = []
        
        # 企業名、人名は残す
        proper_nouns = re.findall(r'\b[A-Z][a-zA-Z]+\b', text)
        
        # 数値は日本語形式に
        text = re.sub(r'(\d+)%', r'\1％', text)
        text = re.sub(r'\$(\d+)', r'\1ドル', text)
        
        # 主要な動詞を日本語化
        verb_map = {
            'shoots up': '急上昇',
            'soared': '急騰',
            'launched': '開始',
            'announced': '発表',
            'increased': '増加',
            'decreased': '減少'
        }
        
        for eng, jpn in verb_map.items():
            text = re.sub(eng, jpn, text, flags=re.IGNORECASE)
        
        # 結果が改善されない場合は、概要として整理
        if cls._is_mostly_english(text):
            # 固有名詞と数値を中心に要約を生成
            summary_parts = []
            if proper_nouns:
                summary_parts.append(proper_nouns[0])
            
            # パーセンテージや数値を抽出
            numbers = re.findall(r'\d+[％%]|\d+ドル', text)
            if numbers:
                summary_parts.extend(numbers[:2])
            
            # IPO、AI、セキュリティなどの重要キーワード
            keywords = re.findall(r'IPO|AI|security|cryptocurrency|blockchain', text, re.IGNORECASE)
            if keywords:
                for kw in keywords[:2]:
                    kw_jp = cls.COMMON_PHRASES.get(kw, kw)
                    summary_parts.append(kw_jp)
            
            if summary_parts:
                text = '、'.join(summary_parts) + 'に関する記事'
            else:
                text = '詳細は原文をご覧ください'
        
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
    
    @classmethod
    def create_summary(cls, title: str, content: str, max_length: int = 200) -> str:
        """
        タイトルと内容から日本語の要約を生成
        
        Args:
            title: 記事タイトル
            content: 記事内容
            max_length: 要約の最大文字数
            
        Returns:
            日本語要約
        """
        # タイトルを簡易翻訳
        translated_title = cls.translate_text(title, max_length=100)
        
        # 内容から重要部分を抽出
        if content:
            # 最初の段落または文を取得
            first_part = content.split('\n')[0] if '\n' in content else content
            first_part = first_part.split('. ')[0] if '. ' in first_part else first_part
            
            # 簡易翻訳
            translated_content = cls.translate_text(first_part, max_length=150)
            
            # 要約を組み立て
            if translated_title and translated_content:
                summary = f"{translated_title}。{translated_content}"
            elif translated_title:
                summary = translated_title
            else:
                summary = translated_content
        else:
            summary = translated_title
        
        # 最大長に収める
        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."
        
        return summary or "記事の要約を生成できませんでした。"