# News Delivery System - tmux使用ガイド

## 📋 概要

このガイドでは、ニュース自動配信システムでのtmux環境の使用方法を説明します。パターンAレイアウトを中心とした効率的な開発・運用環境の構築と操作方法を詳しく解説します。

## 🚀 クイックスタート

### 1. tmux環境のセットアップ

```bash
# ニュース配信システムディレクトリに移動
cd /mnt/e/news-delivery-system

# tmux環境をセットアップ
./scripts/news-tmux-setup.sh

# セッションに接続
tmux attach -t news-main
```

### 2. パターンAレイアウトの適用

```bash
# 別ターミナルまたはtmux内で実行
./scripts/tmux-layout-pattern-a.sh
```

## 📐 パターンAレイアウト構成

```
┌─────────────────┬─────────────────┐
│ 0: システム監視  │ 3: スケジューラー │
├─────────────────┼─────────────────┤
│ 2: 手動実行     │ 4: 設定編集      │
├─────────────────┴─────────────────┤
│ 1: Claude Code指示用ペイン        │
└───────────────────────────────────┘
```

### 各ペインの役割

| ペイン番号 | 名称 | 主な用途 |
|-----------|------|----------|
| 0 | システム監視 | ログ監視、プロセス確認 |
| 1 | Claude Code指示用 | システム分析、修正指示 |
| 2 | 手動実行 | テスト実行、デバッグ |
| 3 | スケジューラー | 定期実行管理 |
| 4 | 設定編集 | 設定ファイル編集 |

## ⌨️ 基本操作

### tmuxキーバインド

| キー | 動作 |
|------|------|
| `Prefix + 0-4` | ペイン番号で切り替え |
| `Prefix + q` | ペイン番号表示 |
| `Prefix + o` | 次のペインに移動 |
| `Prefix + h/j/k/l` | Vim風ペイン移動 |
| `Prefix + \|` | 縦分割 |
| `Prefix + -` | 横分割 |
| `Prefix + r` | 設定リロード |

**注**: Prefixキーはデフォルトで `Ctrl+b` です。

### ウィンドウ操作

| キー | 動作 |
|------|------|
| `Prefix + c` | 新しいウィンドウ作成 |
| `Prefix + n` | 次のウィンドウ |
| `Prefix + p` | 前のウィンドウ |
| `Prefix + 1-9` | ウィンドウ番号で切り替え |
| `Prefix + ,` | ウィンドウ名変更 |

## 🛠️ 専用コマンド

tmux環境では以下の専用コマンドが利用できます：

### システム監視コマンド

```bash
# システム状況確認
news-status

# 健全性チェック
news-health-check

# ログ分析
news-log-analysis

# 全ログ監視
news-logs

# エラーログのみ監視
news-logs-error
```

### システム実行コマンド

```bash
# 日次収集実行
news-daily

# 緊急チェック
news-urgent

# システムチェック
news-check

# ステータス確認
news-status-cmd
```

### スケジューラーコマンド

```bash
# スケジューラー開始
news-scheduler

# スケジュール表示
news-schedule

# 単発実行
news-run-once daily
news-run-once urgent
```

### 設定管理コマンド

```bash
# 設定ディレクトリ表示
news-config

# config.json編集
news-edit-config

# .env編集
news-edit-env
```

### メンテナンスコマンド

```bash
# システムクリーンアップ
news-cleanup

# 緊急停止
news-emergency-stop

# ヘルプ表示
news-help
```

## 📊 各ペインの使用方法

### ペイン0: システム監視

**主な用途**: リアルタイム監視、システム状況確認

```bash
# ログ監視開始
news-logs

# システム状況確認
news-status

# プロセス確認
ps aux | grep python

# ディスク使用量確認
df -h /mnt/e/news-delivery-system
```

**よく使用するコマンド**:
- `news-logs`: 全ログのリアルタイム監視
- `news-status`: システム状況の定期確認
- `news-health-check`: 健全性チェック

### ペイン1: Claude Code指示用

**主な用途**: システム分析、コード修正、トラブルシューティング

```bash
# Claude Codeセッション開始
claude-code

# システム分析依頼例
# "ログエラーを分析して問題箇所を特定してください"
# "パフォーマンスを最適化してください"
# "設定ファイルを調整してください"
```

**使用例**:
1. エラー発生時の原因分析
2. コードの改善提案
3. 設定の最適化
4. 新機能の実装支援

### ペイン2: 手動実行

**主な用途**: テスト実行、デバッグ、一時的な作業

```bash
# システムチェック
news-check

# 日次収集のテスト実行
news-daily

# 設定変更後の動作確認
python main.py check --verbose

# デバッグ実行
python main.py daily --verbose
```

**典型的なワークフロー**:
1. `news-check` でシステム状況確認
2. テスト実行で動作確認
3. 問題があればペイン1のClaude Codeで分析
4. 修正後、再度テスト実行

### ペイン3: スケジューラー

**主な用途**: 定期実行管理、スケジュール監視

```bash
# スケジューラー開始（フォアグラウンド）
news-scheduler

# バックグラウンド実行
news-scheduler &

# スケジュール確認
news-schedule

# 単発テスト実行
news-run-once daily
```

**運用モード**:
- **開発時**: フォアグラウンドで実行、ログを直接確認
- **本番時**: バックグラウンド実行、ログファイルで監視

### ペイン4: 設定編集

**主な用途**: 設定ファイルの編集、設定確認

```bash
# 設定ファイル一覧
news-config

# メイン設定編集
news-edit-config

# 環境変数編集
news-edit-env

# tmux設定編集
nano ../.tmux.conf
```

**設定変更後の確認手順**:
1. 設定ファイル編集
2. ペイン2で `news-check` 実行
3. 問題なければペイン3でスケジューラー再起動

## 🔄 典型的な作業フロー

### 日常運用フロー

1. **セッション開始**
   ```bash
   tmux attach -t news-main
   ```

2. **システム状況確認** (ペイン0)
   ```bash
   news-status
   news-health-check
   ```

3. **スケジューラー確認** (ペイン3)
   ```bash
   news-schedule
   ```

4. **ログ監視開始** (ペイン0)
   ```bash
   news-logs
   ```

### トラブルシューティングフロー

1. **問題発見** (ペイン0)
   - ログでエラーを確認

2. **詳細分析** (ペイン1)
   - Claude Codeでエラー分析

3. **修正実装** (ペイン4)
   - 設定ファイル修正

4. **テスト実行** (ペイン2)
   - 修正内容のテスト

5. **運用再開** (ペイン3)
   - スケジューラー再起動

### 開発・改善フロー

1. **要件分析** (ペイン1)
   - Claude Codeで改善案検討

2. **設定変更** (ペイン4)
   - 設定ファイル編集

3. **テスト実行** (ペイン2)
   - 変更内容のテスト

4. **ログ確認** (ペイン0)
   - 動作状況監視

5. **本番適用** (ペイン3)
   - スケジューラーに反映

## 🔧 カスタマイズ

### .bashrcへの統合

tmuxヘルパー関数を常時利用するため、`.bashrc`に追加：

```bash
# ~/.bashrc に追加
if [[ -f "/mnt/e/news-delivery-system/scripts/tmux-helpers.sh" ]]; then
    source "/mnt/e/news-delivery-system/scripts/tmux-helpers.sh"
fi
```

### 自動起動設定

システム起動時にtmuxセッションを自動開始：

```bash
# ~/.profile または ~/.bash_profile に追加
if command -v tmux &> /dev/null && [[ -z "$TMUX" ]]; then
    if ! tmux has-session -t news-main 2>/dev/null; then
        /mnt/e/news-delivery-system/scripts/news-tmux-setup.sh
    fi
fi
```

## 🚨 トラブルシューティング

### よくある問題と解決方法

#### 1. セッションが見つからない
```bash
# エラー: session not found: news-main
# 解決: セッションを再作成
./scripts/news-tmux-setup.sh
```

#### 2. ペインレイアウトが崩れる
```bash
# 解決: レイアウトを再適用
./scripts/tmux-layout-pattern-a.sh
```

#### 3. コマンドが見つからない
```bash
# エラー: command not found: news-status
# 解決: ヘルパー関数を再読み込み
source scripts/tmux-helpers.sh
```

#### 4. ログが表示されない
```bash
# 確認: ログディレクトリの存在
ls -la data/logs/

# 解決: ディレクトリ作成
mkdir -p data/logs
```

### 緊急時の対応

#### 全プロセス停止
```bash
news-emergency-stop
```

#### セッション強制終了
```bash
tmux kill-session -t news-main
```

#### システム再起動
```bash
./scripts/news-tmux-setup.sh
```

## 📚 参考情報

### tmux公式ドキュメント
- [tmux Manual](https://man.openbsd.org/tmux)
- [tmux Wiki](https://github.com/tmux/tmux/wiki)

### カスタマイズリソース
- [tmux Cheat Sheet](https://tmuxcheatsheet.com/)
- [Oh My Tmux](https://github.com/gpakosz/.tmux)

## 🔄 更新履歴

- **v1.0.0**: 初期版リリース
  - パターンAレイアウト実装
  - 基本ヘルパー関数追加
  - ドキュメント作成

---

このガイドを参考に、効率的なNews Delivery System開発・運用環境をお楽しみください。質問や改善提案があれば、Claude Code指示用ペインでお気軽にお声がけください。