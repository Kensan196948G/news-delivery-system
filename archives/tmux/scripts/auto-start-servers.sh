#!/bin/bash

# Auto Start Servers Script
# ニュース自動配信システム自動起動

# 色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 設定
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TMUX_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$TMUX_DIR")"
PYTHON_ENV_DIR="$PROJECT_ROOT/venv"
ALT_PYTHON_ENV_DIR="$PROJECT_ROOT/news-env"

# ログファイル
LOG_DIR="$TMUX_DIR/logs"
SYSTEM_LOG="$LOG_DIR/news-system.log"
AUTO_START_LOG="$LOG_DIR/auto-start.log"

# ログディレクトリ作成
mkdir -p "$LOG_DIR"

# ログ関数
log() {
    echo -e "$1" | tee -a "$AUTO_START_LOG"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$AUTO_START_LOG"
}

# PIDファイル
SYSTEM_PID_FILE="$LOG_DIR/news-system.pid"

# ヘッダー表示
show_header() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          News Delivery System Controller          ║${NC}"
    echo -e "${CYAN}║         ニュース自動配信システム制御               ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Python仮想環境の確認
check_python_env() {
    if [ -d "$PYTHON_ENV_DIR" ]; then
        return 0  # venv exists
    elif [ -d "$ALT_PYTHON_ENV_DIR" ]; then
        return 0  # news-env exists
    else
        return 1  # no env found
    fi
}

# プロセス終了
kill_process() {
    local pid_file=$1
    local service_name=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log "${YELLOW}Stopping $service_name (PID: $pid)...${NC}"
            kill "$pid" 2>/dev/null
            sleep 2
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null
            fi
        fi
        rm -f "$pid_file"
    fi
}

# Python仮想環境の有効化
activate_python_env() {
    if [ -d "$PYTHON_ENV_DIR" ]; then
        source "$PYTHON_ENV_DIR/bin/activate"
        log "${GREEN}✓ Python virtual environment activated (venv)${NC}"
        return 0
    elif [ -d "$ALT_PYTHON_ENV_DIR" ]; then
        source "$ALT_PYTHON_ENV_DIR/bin/activate"
        log "${GREEN}✓ Python virtual environment activated (news-env)${NC}"
        return 0
    else
        log "${YELLOW}⚠ Python virtual environment not found${NC}"
        return 1
    fi
}

# ニュースシステム起動
start_news_system() {
    log "${BLUE}=== Starting News Delivery System ===${NC}"
    
    # 既存プロセス確認・停止
    kill_process "$SYSTEM_PID_FILE" "News System"
    
    # プロジェクトルートに移動
    cd "$PROJECT_ROOT"
    
    # Python仮想環境有効化
    activate_python_env
    
    # システム起動
    log "${YELLOW}Starting News Delivery System...${NC}"
    
    # システムステータス確認をバックグラウンドで実行
    nohup python main.py status > "$SYSTEM_LOG" 2>&1 &
    local system_pid=$!
    echo "$system_pid" > "$SYSTEM_PID_FILE"
    
    log "${GREEN}✓ News Delivery System started (PID: $system_pid)${NC}"
    log "${GREEN}  Log file: $SYSTEM_LOG${NC}"
    
    # 起動確認（最大10秒待機）
    local count=0
    while [ $count -lt 10 ]; do
        if [ -f "$PROJECT_ROOT/data/logs/news_delivery.log" ]; then
            log "${GREEN}✓ News system is ready${NC}"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        echo -n "."
    done
    
    log "${GREEN}✓ News system started${NC}"
    return 0
}

# ニュースシステム状態確認
check_news_system_status() {
    log "${BLUE}=== Checking News System Status ===${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Python仮想環境有効化
    activate_python_env
    
    # システム状態確認
    log "${YELLOW}Checking system status...${NC}"
    python main.py status
    
    # システムチェック実行
    log "${YELLOW}Running system health check...${NC}"
    python main.py check
    
    return 0
}

# システム状態確認（簡易版）
check_system_status() {
    log "${BLUE}=== Checking System Status ===${NC}"
    
    # PIDファイル確認
    if [ -f "$SYSTEM_PID_FILE" ]; then
        local pid=$(cat "$SYSTEM_PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "${GREEN}✓ News System: Running (PID: $pid)${NC}"
        else
            log "${RED}✗ News System: Process not found${NC}"
        fi
    else
        log "${RED}✗ News System: Not started${NC}"
    fi
    
    # ログファイル確認
    if [ -f "$SYSTEM_LOG" ]; then
        log "${GREEN}✓ System Log: Available${NC}"
        log "${YELLOW}  Recent log entries:${NC}"
        tail -5 "$SYSTEM_LOG" | while read line; do
            log "    $line"
        done
    else
        log "${YELLOW}⚠ System Log: Not found${NC}"
    fi
    
    # 設定ファイル確認
    if [ -f "$PROJECT_ROOT/config/config.json" ]; then
        log "${GREEN}✓ Configuration: Available${NC}"
    else
        log "${RED}✗ Configuration: Missing${NC}"
    fi
}

# システム停止
stop_news_system() {
    log "${BLUE}=== Stopping News System ===${NC}"
    
    kill_process "$SYSTEM_PID_FILE" "News System"
    
    log "${GREEN}✓ News system stopped${NC}"
}

# 再起動
restart_news_system() {
    stop_news_system
    sleep 3
    start_news_system
}

# ニュースシステム起動（全体）
start_all_systems() {
    log "${CYAN}🚀 Starting News Delivery System...${NC}"
    
    # 依存関係確認
    check_dependencies
    
    # ニュースシステム起動
    if start_news_system; then
        sleep 2
        log "${GREEN}🎉 News Delivery System started successfully!${NC}"
        check_system_status
        
        # 操作オプション表示
        echo ""
        echo -e "${CYAN}System started! Available commands:${NC}"
        echo "  python main.py daily    - Run daily news collection"
        echo "  python main.py urgent   - Check urgent news"
        echo "  python main.py check    - System health check"
        echo ""
        
        return 0
    else
        log "${RED}✗ Failed to start News Delivery System${NC}"
        return 1
    fi
}

# 依存関係確認
check_dependencies() {
    log "${BLUE}=== Checking Dependencies ===${NC}"
    
    # Python確認
    if ! command -v python &> /dev/null; then
        if ! command -v python3 &> /dev/null; then
            log "${RED}✗ Python not found${NC}"
            exit 1
        else
            log "${GREEN}✓ Python3: $(python3 --version)${NC}"
        fi
    else
        log "${GREEN}✓ Python: $(python --version)${NC}"
    fi
    
    # pip確認
    if ! command -v pip &> /dev/null; then
        if ! command -v pip3 &> /dev/null; then
            log "${YELLOW}⚠ pip not found${NC}"
        else
            log "${GREEN}✓ pip3: $(pip3 --version)${NC}"
        fi
    else
        log "${GREEN}✓ pip: $(pip --version)${NC}"
    fi
    
    # Python仮想環境確認
    if ! check_python_env; then
        log "${YELLOW}⚠ Python virtual environment not found${NC}"
        log "${YELLOW}  Consider creating: python -m venv venv${NC}"
    fi
    
    # 必要なファイル確認
    if [ ! -f "$PROJECT_ROOT/requirements.txt" ]; then
        log "${YELLOW}⚠ requirements.txt not found${NC}"
    else
        log "${GREEN}✓ requirements.txt found${NC}"
    fi
    
    if [ ! -f "$PROJECT_ROOT/main.py" ]; then
        log "${RED}✗ main.py not found${NC}"
        exit 1
    else
        log "${GREEN}✓ main.py found${NC}"
    fi
}

# ログ表示
show_logs() {
    echo -e "${CYAN}Select log to view:${NC}"
    echo "1. News system log"
    echo "2. Auto-start log"
    echo "3. Main system logs (data/logs/)"
    echo "4. All logs (tail -f)"
    read -p "Choice: " log_choice
    
    case $log_choice in
        1) 
            if [ -f "$SYSTEM_LOG" ]; then
                tail -f "$SYSTEM_LOG"
            else
                echo "System log not found"
            fi
            ;;
        2) tail -f "$AUTO_START_LOG" ;;
        3) 
            if [ -d "$PROJECT_ROOT/data/logs" ]; then
                find "$PROJECT_ROOT/data/logs" -name "*.log" -exec tail -f {} +
            else
                echo "Main logs directory not found"
            fi
            ;;
        4) 
            log_files=()
            [ -f "$SYSTEM_LOG" ] && log_files+=("$SYSTEM_LOG")
            [ -f "$AUTO_START_LOG" ] && log_files+=("$AUTO_START_LOG")
            if [ ${#log_files[@]} -gt 0 ]; then
                tail -f "${log_files[@]}"
            else
                echo "No log files found"
            fi
            ;;
        *) echo "Invalid choice" ;;
    esac
}

# システムサービス作成（Linux systemd）
create_systemd_service() {
    if command -v systemctl &> /dev/null; then
        log "${BLUE}=== Creating systemd service ===${NC}"
        
        cat > /tmp/news-delivery-system.service << EOF
[Unit]
Description=News Delivery System
After=network.target

[Service]
Type=forking
User=$USER
WorkingDirectory=$PROJECT_ROOT
ExecStart=$SCRIPT_DIR/auto-start-servers.sh start
ExecStop=$SCRIPT_DIR/auto-start-servers.sh stop
Restart=always
RestartSec=10
Environment=PATH=/usr/bin:/usr/local/bin

[Install]
WantedBy=multi-user.target
EOF
        
        echo "Systemd service file created at /tmp/news-delivery-system.service"
        echo "To install: sudo cp /tmp/news-delivery-system.service /etc/systemd/system/"
        echo "To enable: sudo systemctl enable news-delivery-system.service"
        echo "To start: sudo systemctl start news-delivery-system.service"
    else
        log "${YELLOW}systemd not available${NC}"
    fi
}

# クリーンアップ（終了時）
cleanup() {
    log "${YELLOW}Cleanup on exit...${NC}"
    # 必要に応じて停止
}

# trap設定
trap cleanup EXIT

# メインメニュー
show_menu() {
    echo ""
    echo -e "${CYAN}=== News Delivery System Menu ===${NC}"
    echo "1. Start news system"
    echo "2. Stop news system"
    echo "3. Restart news system"
    echo "4. Check system status"
    echo "5. Run news collection"
    echo "6. Check urgent news"
    echo "7. System health check"
    echo "8. Show logs"
    echo "9. Create systemd service"
    echo "q. Quit"
    echo ""
}

# メイン処理
main() {
    show_header
    log "${GREEN}🚀 News Delivery System Controller${NC}"
    
    case "${1:-}" in
        "start")
            start_all_systems
            ;;
        "stop")
            stop_news_system
            ;;
        "restart")
            restart_news_system
            ;;
        "status")
            check_system_status
            ;;
        "logs")
            show_logs
            ;;
        "service")
            create_systemd_service
            ;;
        "auto")
            start_all_systems
            exit 0
            ;;
        *)
            # 対話モード
            while true; do
                show_menu
                read -p "Select option: " choice
                
                case $choice in
                    1) start_all_systems ;;
                    2) stop_news_system ;;
                    3) restart_news_system ;;
                    4) check_system_status ;;
                    5) 
                        cd "$PROJECT_ROOT"
                        activate_python_env
                        python main.py daily
                        ;;
                    6) 
                        cd "$PROJECT_ROOT"
                        activate_python_env
                        python main.py urgent
                        ;;
                    7)
                        cd "$PROJECT_ROOT"
                        activate_python_env
                        python main.py check
                        ;;
                    8) show_logs ;;
                    9) create_systemd_service ;;
                    q|Q) 
                        log "${GREEN}Exiting...${NC}"
                        break 
                        ;;
                    *) 
                        echo -e "${RED}Invalid option${NC}" 
                        ;;
                esac
                
                echo ""
                read -p "Press Enter to continue..."
            done
            ;;
    esac
}

# スクリプト実行
main "$@"