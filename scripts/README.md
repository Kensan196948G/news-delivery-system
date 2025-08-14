# News Delivery System - Scripts

このフォルダには、ニュース配信システムの開発・運用に必要なスクリプトが含まれています。

## 📋 スクリプト一覧

### 🔧 tmux環境セットアップ

| ファイル名 | 説明 | 用途 |
|-----------|------|------|
| `simple-tmux-setup.sh` | **メイン** tmux環境セットアップ | パターンAレイアウト作成・Claude Yolo自動起動 |
| `fix-claude-startup.sh` | Claude Yolo起動修正 | 既存セッションでClaude Yolo再起動 |
| `start-claude-interactive.sh` | **推奨** Claude Yolo確実起動 | インタラクティブモードで確実起動 |
| `tmux-pane-commander.sh` | **コア** ペイン間指示システム | ペイン4から他ペインへの指示送信 |
| `tmux-helpers.sh` | tmux用ヘルパー関数 | エイリアス・便利コマンド集 |
| `tmux-pane-title.sh` | ペインタイトル自動設定 | アイコン付きタイトル設定 |

### 🧪 テスト・検証

| ファイル名 | 説明 | 用途 |
|-----------|------|------|
| `test-tmux-pane-system.sh` | tmuxシステム総合テスト | 全機能の動作確認・レポート生成 |

## 🚀 使用方法

### 初回セットアップ
```bash
# tmux環境を初回作成
./scripts/simple-tmux-setup.sh

# セッションに接続
tmux attach -t news-main
```

### 日常使用
```bash
# 既存セッションでClaude Yolo確実起動（推奨）
./scripts/start-claude-interactive.sh

# または、修正版Claude Yolo起動
./scripts/fix-claude-startup.sh

# ペイン間指示コマンド例
./scripts/tmux-pane-commander.sh help
./scripts/tmux-pane-commander.sh send-to-manual "news-daily"
./scripts/tmux-pane-commander.sh quick-health-check
```

### システムテスト
```bash
# 全機能テスト実行
./scripts/test-tmux-pane-system.sh
```

## 📐 tmux構成（パターンA）

```
┌─────────────────┬─────────────────┐
│ 0: 🖥️ システム監視 │ 2: ⏰ スケジューラー │
├─────────────────┼─────────────────┤
│ 1: 🔧 手動実行    │ 3: ⚙️ 設定編集     │
├─────────────────┴─────────────────┤
│ 4: 🤖 Claude指示用ペイン          │
└───────────────────────────────────┘
```

## 🎯 主要機能

- **アイコン付きペインタイトル**: 各ペインの役割が一目で分かる
- **ペイン間指示システム**: ペイン4から他ペインに正確な指示送信
- **Claude Yolo自動起動**: 全ペインでClaude Yolo自動起動
- **便利コマンド群**: エイリアスとヘルパー関数で効率的な操作

## 📝 注意事項

- 必ず `simple-tmux-setup.sh` から開始してください
- Claude Yoloパスは環境に応じて調整が必要な場合があります
- セッション名は `news-main` で固定されています