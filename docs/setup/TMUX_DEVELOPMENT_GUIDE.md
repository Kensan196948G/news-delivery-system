# 🖥️ News Delivery System - TMUX開発環境ガイド

ニュース配信システム専用のtmux開発環境の完全ガイドです。パターンAレイアウトとClaude Yolo統合により、効率的な開発環境を提供します。

## 📐 システム概要

### 🎯 パターンAレイアウト構成

```
┌─────────────────┬─────────────────┐
│ 0: 🖥️ システム監視 │ 2: ⏰ スケジューラー │
│ (40x6)          │ (39x6)          │
├─────────────────┼─────────────────┤
│ 1: 🔧 手動実行    │ 3: ⚙️ 設定編集     │
│ (40x7)          │ (39x7)          │
├─────────────────┴─────────────────┤
│ 4: 🤖 Claude指示用ペイン (80x8)   │
└───────────────────────────────────┘
```

### 🎯 各ペインの役割

| ペイン | アイコン | 役割 | 主な用途 |
|--------|----------|------|----------|
| **0** | 🖥️ | システム監視 | ログ監視・システム状況確認・エラー検出 |
| **1** | 🔧 | 手動実行 | テスト実行・日次収集・緊急処理 |
| **2** | ⏰ | スケジューラー | 自動実行制御・スケジュール管理 |
| **3** | ⚙️ | 設定編集 | 設定ファイル編集・パラメータ調整 |
| **4** | 🤖 | Claude指示用 | **メイン制御ペイン** - 他ペインへの指示送信 |

## 🚀 セットアップ

### 1. 初回環境構築

```bash
# tmux環境を作成（アイコン付きタイトル・Claude Yolo自動起動）
./scripts/simple-tmux-setup.sh

# セッションに接続
tmux attach -t news-main
```

### 2. Claude Yolo起動確認

各ペインでClaude Yoloが起動していない場合：

```bash
# 全ペインでClaude Yolo再起動
./scripts/fix-claude-startup.sh
```

### 3. システムテスト

```bash
# 全機能動作確認
./scripts/test-tmux-pane-system.sh
```

## 🎯 ペイン間指示システム

### 基本的な指示送信

```bash
# 基本形式
./scripts/tmux-pane-commander.sh send-to-pane <ペイン番号> <コマンド>

# 例：手動実行ペインで日次収集開始
./scripts/tmux-pane-commander.sh send-to-manual "python main.py daily --verbose"

# 例：システム監視ペインでログ確認
./scripts/tmux-pane-commander.sh send-to-monitor "tail -f data/logs/*.log"
```

### 役割別指示送信

```bash
# システム監視ペイン（ペイン0）に指示
./scripts/tmux-pane-commander.sh send-to-monitor <コマンド>

# 手動実行ペイン（ペイン1）に指示  
./scripts/tmux-pane-commander.sh send-to-manual <コマンド>

# スケジューラーペイン（ペイン2）に指示
./scripts/tmux-pane-commander.sh send-to-scheduler <コマンド>

# 設定編集ペイン（ペイン3）に指示
./scripts/tmux-pane-commander.sh send-to-config <コマンド>
```

### 複数ペイン同時指示

```bash
# 複数ペインに同時送信
./scripts/tmux-pane-commander.sh send-to-multiple "0,1,2,3" "clear"

# 例：全作業ペインでシステム状況確認
./scripts/tmux-pane-commander.sh send-to-multiple "0,1,2,3" "python main.py status"
```

## ⚡ クイック実行コマンド

### 日常的な操作

```bash
# 日次ニュース収集実行
./scripts/tmux-pane-commander.sh quick-daily

# 緊急ニュースチェック実行  
./scripts/tmux-pane-commander.sh quick-urgent

# システムログ監視開始
./scripts/tmux-pane-commander.sh quick-logs

# スケジューラー開始
./scripts/tmux-pane-commander.sh quick-scheduler-start

# 全ペイン健全性チェック
./scripts/tmux-pane-commander.sh quick-health-check

# 全ペインクリア
./scripts/tmux-pane-commander.sh clear-all
```

## 📋 便利なエイリアス

tmux環境内で使用可能な短縮コマンド：

```bash
# ペイン間指示（短縮形）
send-monitor "コマンド"      # システム監視ペインに送信
send-manual "コマンド"       # 手動実行ペインに送信  
send-scheduler "コマンド"    # スケジューラーペインに送信
send-config "コマンド"       # 設定編集ペインに送信

# クイック実行（短縮形）
quick-daily        # 日次収集実行
quick-urgent       # 緊急チェック実行
quick-logs         # ログ監視開始
quick-scheduler    # スケジューラー開始
quick-health       # 健全性チェック
quick-clear        # 全ペインクリア

# ペイン操作
pane 0            # ペイン0に切り替え
pane 1            # ペイン1に切り替え
current-pane      # 現在のペイン情報表示

# システム操作
news-help         # 利用可能コマンド一覧
news-status       # システム状況表示
news-daily        # 日次収集実行
news-check        # システムヘルスチェック
```

## 🔧 tmux基本操作

### キーバインド

| キー | 操作 |
|------|------|
| `Ctrl+B → 0-4` | 指定ペインに切り替え |
| `Ctrl+B → q` | ペイン番号表示 |
| `Ctrl+B → o` | 次のペインに移動 |
| `Ctrl+B → h/j/k/l` | Vim風ペイン移動 |
| `Ctrl+B → r` | tmux設定リロード |
| `Ctrl+B → d` | セッションから切断 |

### セッション管理

```bash
# セッション一覧表示
tmux list-sessions

# セッションに接続  
tmux attach -t news-main

# セッションから切断（セッションは継続）
Ctrl+B → d

# セッション終了
./scripts/tmux-pane-commander.sh kill-session  # または
tmux kill-session -t news-main
```

## 📊 システム監視とデバッグ

### ペイン構成確認

```bash
# 現在のペイン構成表示
./scripts/tmux-pane-commander.sh show-panes

# ペイン詳細情報  
tmux list-panes -t news-main -F "#{pane_index}: #{pane_title} (#{pane_width}x#{pane_height})"
```

### コマンド履歴確認

```bash
# 送信したコマンドの履歴表示
./scripts/tmux-pane-commander.sh show-history

# ログファイル確認
tail -f data/logs/tmux_commands.log
```

### トラブルシューティング

```bash
# tmux設定確認
tmux show-options -g | grep pane

# セッション詳細確認  
tmux display-message -p "Session: #S, Window: #W, Pane: #P"

# ペインタイトル手動設定
tmux select-pane -t news-main:0 -T "🖥️ システム監視"
```

## 🎯 開発ワークフロー例

### 1. 日常的な開発作業

```bash
# 1. tmux環境起動
./scripts/simple-tmux-setup.sh
tmux attach -t news-main

# 2. Claude指示用ペイン（ペイン4）から作業開始
# ペイン4で以下を実行：

# システム状況確認
quick-health

# ログ監視開始  
send-monitor "news-logs"

# 設定ファイル確認
send-config "ls -la && cat config.json | jq ."

# テスト実行
send-manual "python main.py check && python main.py status"
```

### 2. 新機能開発時

```bash
# 1. 全ペインクリア
quick-clear

# 2. 開発環境準備
send-config "nano config/config.json"  # 設定編集
send-manual "python -m pytest tests/"  # テスト実行
send-monitor "tail -f data/logs/news_system.log"  # ログ監視

# 3. 機能テスト  
send-manual "python main.py daily --verbose"

# 4. システム統合テスト
quick-health
```

### 3. 問題調査時

```bash
# 1. エラー確認
send-monitor "grep ERROR data/logs/*.log | tail -10"

# 2. システム状況確認
send-manual "python main.py check"

# 3. API状況確認  
send-manual "python tools/check_api_keys.py"

# 4. 設定確認
send-config "cat .env | grep -v KEY && ls -la config/"
```

## 📝 カスタマイズ

### Claude Yoloパス変更

`scripts/simple-tmux-setup.sh`内の`CLAUDE_CMD`を編集：

```bash
# デフォルト
CLAUDE_CMD="/home/kensa/.nvm/versions/node/v22.16.0/bin/claude-yolo"

# カスタム例  
CLAUDE_CMD="/usr/local/bin/claude-yolo"
```

### ペインタイトルカスタマイズ

`scripts/tmux-pane-title.sh`を編集してタイトルを変更可能。

### 新しいクイックコマンド追加

`scripts/tmux-pane-commander.sh`に新しい関数を追加してカスタムコマンドを作成可能。

## 🚨 注意事項

- **セッション名固定**: `news-main`で固定されています
- **Claude Yolo依存**: 各ペインでClaude Yoloが必要です
- **パス依存**: スクリプトは`/mnt/e/news-delivery-system`ベースで動作
- **権限要件**: tmux設定ファイルの書き込み権限が必要

## 📞 サポート

### 問題発生時の確認手順

1. **セッション確認**: `tmux list-sessions`
2. **ペイン確認**: `./scripts/tmux-pane-commander.sh show-panes`  
3. **システムテスト**: `./scripts/test-tmux-pane-system.sh`
4. **再セットアップ**: `./scripts/simple-tmux-setup.sh`

### ログファイル

- **コマンド履歴**: `data/logs/tmux_commands.log`
- **テスト結果**: `data/logs/tmux_test_report_*.log`

---

**💡 ヒント**: ペイン4（Claude指示用）を活用して、効率的な開発環境を構築しましょう！