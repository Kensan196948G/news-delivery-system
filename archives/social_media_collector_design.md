# ソーシャルメディア監視機能 実装計画

## ファイル構成

- `src/collectors/social_media_collector.py`
- `src/collectors/twitter_collector.py`
- `src/collectors/facebook_collector.py`
- `src/collectors/instagram_collector.py`

## 実装手順

### 1. 各ソーシャルメディアプラットフォームのAPIクライアントライブラリの実装

- tweepy (Twitter API)
- facebook-sdk (Facebook API)
- instagrapi (Instagram API)

### 2. SocialMediaCollectorクラスの実装

- `base_collector.py`を継承。
- 各プラットフォームのcollectorを呼び出す。
- 取得したデータをArticleオブジェクトに変換する。

### 3. 各プラットフォームのcollectorの実装

- TwitterCollectorクラス (`twitter_collector.py`)
- FacebookCollectorクラス (`facebook_collector.py`)
- InstagramCollectorクラス (`instagram_collector.py`)
- 各クラスは`base_collector.py`を継承。

### 4. 設定ファイルの更新

- `config.json`や`.env`にAPIキーなどの設定を追加。

### 5. データベーススキーマの更新

- ソーシャルメディア投稿用のテーブルを追加。

### 6. テストコードの作成

- 各collectorのテストコードを作成。