#!/bin/bash
#
# Robust Cron Runner Script
# 堅牢なCron実行スクリプト - 自動修復機能付き
#
# エラー検知・自動修復・配信確認のループ実行
#

# 設定変数 - スクリプトの場所から相対パスで設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/venv"
PYTHON_PATH="$VENV_PATH/bin/python"
MAIN_SCRIPT="$PROJECT_ROOT/src/main.py"
LOG_DIR="$PROJECT_ROOT/logs"
ERROR_LOG="$LOG_DIR/cron_errors_$(date +%Y%m).log"
SUCCESS_LOG="$LOG_DIR/cron_success_$(date +%Y%m).log"

# ログディレクトリ作成
mkdir -p "$LOG_DIR"

# 実行時刻
EXECUTION_TIME=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$EXECUTION_TIME] Starting robust cron runner" >> "$SUCCESS_LOG"

# エラー処理関数
handle_error() {
    local error_message="$1"
    local error_context="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$timestamp] ERROR in $error_context: $error_message" >> "$ERROR_LOG"
    
    # エラー通知送信
    source "$SCRIPT_DIR/error_notifier.sh"
    notify_news_delivery_error "$(date '+%H:%M')" "$error_message" "$ERROR_LOG"
    
    # 自動修復試行
    attempt_auto_repair "$error_context" "$error_message"
}

# 自動修復関数
attempt_auto_repair() {
    local context="$1"
    local error="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$timestamp] Attempting auto-repair for: $context" >> "$ERROR_LOG"
    
    case "$context" in
        "venv_missing"|"python_error")
            echo "[$timestamp] Recreating virtual environment..." >> "$ERROR_LOG"
            
            # 仮想環境再作成
            if [ -d "$VENV_PATH" ]; then
                rm -rf "$VENV_PATH"
            fi
            
            python3 -m venv "$VENV_PATH"
            if [ $? -eq 0 ]; then
                source "$VENV_PATH/bin/activate"
                
                # 依存関係インストール
                if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
                    "$PYTHON_PATH" -m pip install --upgrade pip
                    "$PYTHON_PATH" -m pip install -r "$PROJECT_ROOT/requirements.txt"
                    
                    if [ $? -eq 0 ]; then
                        echo "[$timestamp] Virtual environment recreated successfully" >> "$SUCCESS_LOG"
                        return 0
                    fi
                fi
            fi
            
            echo "[$timestamp] Failed to recreate virtual environment" >> "$ERROR_LOG"
            return 1
            ;;
            
        "permission_error")
            echo "[$timestamp] Fixing permissions..." >> "$ERROR_LOG"
            
            # 実行権限修正
            chmod +x "$PROJECT_ROOT/scripts/"*.sh 2>/dev/null
            chmod +x "$MAIN_SCRIPT" 2>/dev/null
            
            # ディレクトリ権限修正
            chmod -R u+rw "$PROJECT_ROOT/logs" 2>/dev/null
            chmod -R u+rw "$PROJECT_ROOT/config" 2>/dev/null
            
            echo "[$timestamp] Permissions fixed" >> "$SUCCESS_LOG"
            return 0
            ;;
            
        "syntax_error")
            echo "[$timestamp] Detected Python syntax error, attempting code repair..." >> "$ERROR_LOG"
            
            # Git status確認（変更がある場合はリセット）
            cd "$PROJECT_ROOT"
            if command -v git >/dev/null 2>&1; then
                if git status --porcelain | grep -q "^.M"; then
                    echo "[$timestamp] Resetting modified files..." >> "$ERROR_LOG"
                    git checkout -- src/main.py 2>/dev/null || true
                    
                    # リセット後にテスト
                    if "$PYTHON_PATH" -m py_compile src/main.py 2>/dev/null; then
                        echo "[$timestamp] Syntax error fixed by git reset" >> "$SUCCESS_LOG"
                        return 0
                    fi
                fi
            fi
            
            echo "[$timestamp] Could not automatically fix syntax error" >> "$ERROR_LOG"
            return 1
            ;;
            
        "module_error"|"import_error")
            echo "[$timestamp] Reinstalling Python dependencies..." >> "$ERROR_LOG"
            
            if [ -f "$VENV_PATH/bin/activate" ]; then
                source "$VENV_PATH/bin/activate"
                "$PYTHON_PATH" -m pip install --upgrade pip
                "$PYTHON_PATH" -m pip install -r "$PROJECT_ROOT/requirements.txt" --force-reinstall
                
                if [ $? -eq 0 ]; then
                    echo "[$timestamp] Dependencies reinstalled successfully" >> "$SUCCESS_LOG"
                    return 0
                fi
            fi
            
            echo "[$timestamp] Failed to reinstall dependencies" >> "$ERROR_LOG"
            return 1
            ;;
            
        "network_error"|"api_error")
            echo "[$timestamp] Network/API error detected, waiting and retrying..." >> "$ERROR_LOG"
            
            # ネットワーク接続テスト
            if ping -c 1 google.com >/dev/null 2>&1; then
                echo "[$timestamp] Network connectivity confirmed" >> "$SUCCESS_LOG"
                
                # 5分待機してリトライ
                sleep 300
                return 0
            else
                echo "[$timestamp] Network connectivity failed" >> "$ERROR_LOG"
                return 1
            fi
            ;;
            
        *)
            echo "[$timestamp] Unknown error context: $context" >> "$ERROR_LOG"
            return 1
            ;;
    esac
}

# 事前チェック関数
pre_execution_check() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # プロジェクトディレクトリ確認
    if [ ! -d "$PROJECT_ROOT" ]; then
        handle_error "Project directory not found: $PROJECT_ROOT" "directory_missing"
        return 1
    fi
    
    # 仮想環境確認
    if [ ! -f "$PYTHON_PATH" ]; then
        handle_error "Python executable not found: $PYTHON_PATH" "venv_missing"
        
        # 自動修復試行
        if attempt_auto_repair "venv_missing" "Python executable not found"; then
            echo "[$timestamp] Virtual environment auto-repaired" >> "$SUCCESS_LOG"
        else
            return 1
        fi
    fi
    
    # メインスクリプト確認
    if [ ! -f "$MAIN_SCRIPT" ]; then
        handle_error "Main script not found: $MAIN_SCRIPT" "script_missing"
        return 1
    fi
    
    # 実行権限確認
    if [ ! -x "$PYTHON_PATH" ]; then
        handle_error "Python executable not executable: $PYTHON_PATH" "permission_error"
        attempt_auto_repair "permission_error" "Python not executable"
    fi
    
    echo "[$timestamp] Pre-execution checks completed successfully" >> "$SUCCESS_LOG"
    return 0
}

# メイン実行関数
execute_news_system() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local retry_count=0
    local max_retries=3
    
    while [ $retry_count -lt $max_retries ]; do
        echo "[$timestamp] Executing news delivery system (attempt $((retry_count + 1))/$max_retries)" >> "$SUCCESS_LOG"
        
        # 仮想環境アクティベート
        if [ -f "$VENV_PATH/bin/activate" ]; then
            source "$VENV_PATH/bin/activate"
        else
            handle_error "Virtual environment activation failed" "venv_missing"
            if ! attempt_auto_repair "venv_missing" "Activation failed"; then
                return 1
            fi
            source "$VENV_PATH/bin/activate"
        fi
        
        # メインスクリプト実行
        cd "$PROJECT_ROOT"
        
        # エラー出力をキャプチャして分析
        local error_output
        error_output=$("$PYTHON_PATH" "$MAIN_SCRIPT" --mode daily 2>&1)
        local exit_code=$?
        
        if [ $exit_code -eq 0 ]; then
            echo "[$timestamp] News delivery system executed successfully" >> "$SUCCESS_LOG"
            echo "$error_output" >> "$SUCCESS_LOG"
            
            # 配信確認
            verify_email_delivery
            
            return 0
        else
            echo "[$timestamp] News delivery system failed with exit code: $exit_code" >> "$ERROR_LOG"
            echo "$error_output" >> "$ERROR_LOG"
            
            # エラー内容を分析して適切な修復を実行
            analyze_and_repair_error "$error_output"
            
            retry_count=$((retry_count + 1))
            
            if [ $retry_count -lt $max_retries ]; then
                echo "[$timestamp] Waiting 60 seconds before retry..." >> "$ERROR_LOG"
                sleep 60
            fi
        fi
    done
    
    echo "[$timestamp] News delivery system failed after $max_retries attempts" >> "$ERROR_LOG"
    send_failure_notification
    return 1
}

# エラー分析・修復関数
analyze_and_repair_error() {
    local error_output="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$timestamp] Analyzing error output for automatic repair..." >> "$ERROR_LOG"
    
    # 構文エラー検出
    if echo "$error_output" | grep -i "syntaxerror\|expected.*except\|expected.*finally\|closing parenthesis.*does not match" >/dev/null; then
        attempt_auto_repair "syntax_error" "Python syntax error"
        
    # モジュールエラー検出
    elif echo "$error_output" | grep -i "modulenotfounderror\|importerror\|no module named" >/dev/null; then
        attempt_auto_repair "module_error" "Module import failed"
        
    # ネットワークエラー検出
    elif echo "$error_output" | grep -i "connectionerror\|timeout\|network\|dns" >/dev/null; then
        attempt_auto_repair "network_error" "Network connectivity issue"
        
    # API エラー検出
    elif echo "$error_output" | grep -i "429\|rate limit\|api.*error\|unauthorized" >/dev/null; then
        attempt_auto_repair "api_error" "API access issue"
        
    # 権限エラー検出
    elif echo "$error_output" | grep -i "permission denied\|access denied" >/dev/null; then
        attempt_auto_repair "permission_error" "Permission issue"
        
    # Python環境エラー検出
    elif echo "$error_output" | grep -i "python.*not found\|command not found" >/dev/null; then
        attempt_auto_repair "python_error" "Python environment issue"
        
    else
        echo "[$timestamp] Unknown error pattern, no specific repair available" >> "$ERROR_LOG"
    fi
}

# 配信確認関数
verify_email_delivery() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Gmail配信ログをチェック
    local today=$(date '+%Y-%m-%d')
    
    if grep -q "Daily report sent successfully" "$SUCCESS_LOG" 2>/dev/null ||
       grep -q "$today.*sent successfully" "$LOG_DIR"/*.log 2>/dev/null; then
        echo "[$timestamp] Email delivery confirmed" >> "$SUCCESS_LOG"
        return 0
    else
        echo "[$timestamp] Email delivery not confirmed" >> "$ERROR_LOG"
        
        # 配信失敗通知
        send_delivery_failure_notification
        return 1
    fi
}

# 失敗通知関数
send_failure_notification() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # 詳細エラー情報収集
    local error_details="News delivery system failed after multiple retry attempts.\n\nLast errors:\n$(tail -n 20 "$ERROR_LOG" 2>/dev/null || echo 'No error log available')\n\nLog files:\n- Success log: $SUCCESS_LOG\n- Error log: $ERROR_LOG"
    
    # エラー通知送信
    source "$SCRIPT_DIR/error_notifier.sh"
    notify_news_delivery_error "$(date '+%H:%M')" "$error_details" "$ERROR_LOG"
    
    echo "[$timestamp] Critical failure notification sent to administrator" >> "$ERROR_LOG"
}

# 配信失敗通知関数
send_delivery_failure_notification() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$timestamp] Sending delivery failure notification..." >> "$ERROR_LOG"
    
    # エラー詳細収集
    local error_details="The news delivery system executed but email delivery was not confirmed.\n\nPlease check Gmail configuration and connectivity.\n\nSystem Status:\n- Timestamp: $timestamp\n- Logs: $(ls -la "$LOG_DIR"/*.log 2>/dev/null || echo 'No logs found')"
    
    # エラー通知送信
    source "$SCRIPT_DIR/error_notifier.sh"
    notify_news_delivery_error "$(date '+%H:%M')" "$error_details" "$ERROR_LOG"
    
    echo "[$timestamp] Delivery failure notification sent" >> "$ERROR_LOG"
}

# メイン実行フロー
main() {
    local start_time=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$start_time] ======= Robust Cron Runner Started =======" >> "$SUCCESS_LOG"
    
    # 事前チェック
    if ! pre_execution_check; then
        echo "[$start_time] Pre-execution checks failed" >> "$ERROR_LOG"
        exit 1
    fi
    
    # メイン実行
    if execute_news_system; then
        local end_time=$(date '+%Y-%m-%d %H:%M:%S')
        echo "[$end_time] ======= Robust Cron Runner Completed Successfully =======" >> "$SUCCESS_LOG"
        exit 0
    else
        local end_time=$(date '+%Y-%m-%d %H:%M:%S')
        echo "[$end_time] ======= Robust Cron Runner Failed =======" >> "$ERROR_LOG"
        exit 1
    fi
}

# スクリプト実行
main "$@"