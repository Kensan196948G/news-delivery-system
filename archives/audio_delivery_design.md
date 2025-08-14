# 音声ニュース配信機能 実装計画

## ファイル構成

- `src/services/audio_delivery.py`

## 実装手順

### 1. TTSエンジンの選定と実装

- Google Cloud Text-to-SpeechまたはAmazon Pollyの選定
- 音声の種類（男性/女性、言語）、読み上げ速度、強調表示するキーワードなどのカスタマイズオプションの実装

### 2. AudioDeliveryServiceクラスの実装

- 既存のserviceを参考に実装
- 音声ファイル生成処理の実装
- 音声ファイルの配信処理の実装（メール添付、クラウドストレージアップロードなど）

### 3. 設定ファイルの更新

- `config.json`や`.env`にTTSエンジンの設定を追加

### 4. テストコードの作成

- AudioDeliveryServiceのテストコードを作成

## 実装詳細

### TTSエンジンの選定

- Google Cloud Text-to-Speechを使用する。
- 理由: 日本語対応が充実しており、音質も良好。

### AudioDeliveryServiceクラス

- `email_delivery.py`を参考に実装。
- 音声ファイル生成処理:
  - 記事をテキストから音声に変換。
  - 音声ファイル（MP3）を生成。
- 音声ファイルの配信処理:
  - メール添付で配信。
  - クラウドストレージ（Google Driveなど）にアップロードしてリンクを配信。

### 設定ファイル

- `.env`にGoogle CloudのAPIキーを追加。
- `config.json`に音声の種類、読み上げ速度などの設定を追加。

### テストコード

- `tests/services/test_audio_delivery.py`を作成。
- 音声ファイル生成処理のテスト。
- 音声ファイル配信処理のテスト。