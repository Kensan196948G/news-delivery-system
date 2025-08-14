"""
Source Name Translator
ニュースソース名の日本語化モジュール
"""

class SourceTranslator:
    """ニュースソース名を日本語に変換"""
    
    # 主要メディアの日本語変換マッピング
    SOURCE_MAPPING = {
        # 国際メディア
        'BBC News': 'BBC（英国放送協会）',
        'CNN': 'CNN（米国）',
        'Cable News Network': 'CNN（米国）',
        'Reuters': 'ロイター通信',
        'The Associated Press': 'AP通信',
        'NPR': 'NPR（米国公共ラジオ）',
        'Al Jazeera': 'アルジャジーラ',
        'Al-Monitor': 'アル・モニター（中東報道）',
        'Forbes': 'フォーブス',
        'Business Insider': 'ビジネスインサイダー',
        'The Verge': 'ザ・ヴァージ（テクノロジー）',
        'TechCrunch': 'テッククランチ',
        'Gizmodo': 'ギズモード',
        'Wired': 'ワイアード',
        'Ars Technica': 'アーステクニカ',
        'ZDNet': 'ZDネット',
        'The Guardian': 'ガーディアン紙（英国）',
        'The New York Times': 'ニューヨーク・タイムズ',
        'The Washington Post': 'ワシントン・ポスト',
        'Wall Street Journal': 'ウォールストリート・ジャーナル',
        'Financial Times': 'フィナンシャル・タイムズ',
        'The Economist': 'エコノミスト誌',
        'Bloomberg': 'ブルームバーグ',
        'Yahoo Entertainment': 'ヤフー（エンタメ）',
        'Yahoo Finance': 'ヤフーファイナンス',
        'Yahoo News': 'ヤフーニュース',
        'The Boston Globe': 'ボストン・グローブ紙',
        'UPI News': 'UPI通信',
        'Breitbart News Network': 'ブライトバート・ニュース',
        'Benzinga': 'ベンジンガ（金融）',
        'WDIV ClickOnDetroit': 'デトロイト地方局',
        'Gizmodo.com': 'ギズモード',
        
        # 日本メディア
        'NHK': 'NHK（日本放送協会）',
        'Asahi Shimbun': '朝日新聞',
        'Yomiuri Shimbun': '読売新聞',
        'Mainichi Shimbun': '毎日新聞',
        'Nikkei': '日本経済新聞',
        'Kyodo News': '共同通信',
        'Jiji Press': '時事通信',
        
        # テクノロジー・セキュリティ
        'SecurityWeek': 'セキュリティウィーク',
        'Dark Reading': 'ダークリーディング',
        'Threatpost': 'スレットポスト',
        'Bleeping Computer': 'ブリーピングコンピュータ',
        'The Hacker News': 'ハッカーニュース',
    }
    
    @classmethod
    def translate(cls, source_name: str) -> str:
        """
        ソース名を日本語に変換
        
        Args:
            source_name: 元のソース名
            
        Returns:
            日本語化されたソース名
        """
        if not source_name:
            return "不明なソース"
            
        # 完全一致を確認
        if source_name in cls.SOURCE_MAPPING:
            return cls.SOURCE_MAPPING[source_name]
        
        # 部分一致を確認（大文字小文字を無視）
        source_lower = source_name.lower()
        for original, japanese in cls.SOURCE_MAPPING.items():
            if original.lower() in source_lower or source_lower in original.lower():
                return japanese
        
        # マッピングにない場合は元の名前を返す（但し「ニュース」を追加）
        if any(char.isalpha() and ord(char) < 128 for char in source_name):
            # 英語名の場合
            return f"{source_name}（海外メディア）"
        else:
            # 日本語または他の言語
            return source_name
    
    @classmethod
    def get_category_name(cls, category: str) -> str:
        """カテゴリ名を日本語に変換"""
        category_mapping = {
            'domestic_social': '国内社会',
            'international_social': '国際社会',
            'domestic_economy': '国内経済',
            'international_economy': '国際経済',
            'tech': 'IT/AI',
            'security': 'セキュリティ',
            'DOMESTIC_SOCIAL': '国内社会',
            'INTERNATIONAL_SOCIAL': '国際社会',
            'DOMESTIC_ECONOMY': '国内経済',
            'INTERNATIONAL_ECONOMY': '国際経済',
            'TECH': 'IT/AI',
            'SECURITY': 'セキュリティ',
        }
        return category_mapping.get(category, category)