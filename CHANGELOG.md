# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2025-08-14

### Added
- 🌐 英語記事の完全日本語翻訳機能
  - DeepL API有料版対応（自動エンドポイント切り替え）
  - SimpleTranslatorによるフォールバック翻訳
  - 英語・日本語記事の分離表示機能
  - 原文と翻訳文の折りたたみ表示

### Changed
- 📧 メールレポートの改善
  - 翻訳済みタイトルと原題を分離表示
  - 日本語訳を優先的に表示
  - 英語原文を「詳細を表示」で折りたたみ可能に
- 🔄 DeepL API設定の自動判定
  - 無料版（:fx付きキー）と有料版を自動識別
  - 適切なAPIエンドポイントを自動選択

### Fixed
- 🐛 NoneType比較エラーの修正
  - importance_scoreとcvss_scoreのNoneチェック追加
  - HTMLレポート生成時のエラーハンドリング改善
- 🔧 翻訳処理のエラーハンドリング強化
  - DeepL API失敗時の自動フォールバック
  - 翻訳失敗時の日本語説明追加

## [1.2.0] - 2025-08-13

### Added
- 🤖 完全自動運用サイクル実装
  - 30分〜1時間おきの自動実行
  - メール配信無効化オプション
  - CodeRabbitAIレート制限対策

### Changed
- ⚙️ 新仕様対応
  - 1時間以内自動フロー
  - 成功メール通知

## [1.1.0] - 2025-08-12

### Added
- 🔒 セキュリティ自動監視機能
  - GitHub Actions統合
  - 脆弱性自動検出
  - Issue自動作成

### Changed
- 📚 ドキュメント管理の自動化
  - README自動更新
  - API文書生成

## [1.0.0] - 2025-08-11

### Added
- 🚀 初回リリース
  - ニュース自動収集機能
  - AI要約・分析機能
  - メール配信機能
  - Linux cron対応