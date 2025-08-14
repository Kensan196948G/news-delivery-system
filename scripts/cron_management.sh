#!/bin/bash
"""
Cron Management Script for News Delivery System
Cronの管理用スクリプト
"""

PROJECT_PATH="/media/kensan/LinuxHDD/news-delivery-system"

show_help() {
    echo "📋 News Delivery System - Cron Management"
    echo "========================================"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  install    Install cron jobs for automated news delivery"
    echo "  remove     Remove news delivery cron jobs"
    echo "  status     Show current cron status"
    echo "  logs       Show recent cron execution logs"
    echo "  test       Test single news delivery execution"
    echo "  help       Show this help message"
    echo ""
    echo "Scheduled times:"
    echo "  🌅 Morning: 07:00 JST"
    echo "  🌞 Noon:    12:00 JST"
    echo "  🌆 Evening: 18:00 JST"
    echo "  🗄️ Backup:  23:00 JST (Sundays)"
}

install_cron() {
    echo "⚙️ Installing News Delivery System cron jobs..."
    
    # Make scripts executable
    chmod +x "$PROJECT_PATH/scripts/setup_cron.sh"
    chmod +x "$PROJECT_PATH/scripts/backup_data.py"
    
    # Run the setup script
    bash "$PROJECT_PATH/scripts/setup_cron.sh"
    
    echo "✅ Cron installation completed!"
}

remove_cron() {
    echo "🗑️ Removing News Delivery System cron jobs..."
    
    # Create temporary file with current crontab minus our jobs
    TEMP_CRON=$(mktemp)
    
    # Get current crontab and filter out our jobs
    crontab -l 2>/dev/null | grep -v "News Delivery System" | grep -v "src/main.py" | grep -v "backup_data.py" > "$TEMP_CRON"
    
    # Install filtered crontab
    crontab "$TEMP_CRON"
    
    # Clean up
    rm "$TEMP_CRON"
    
    echo "✅ Cron jobs removed!"
}

show_status() {
    echo "📊 Current Cron Status"
    echo "====================="
    echo ""
    
    # Show current crontab
    echo "📋 Active cron jobs:"
    crontab -l 2>/dev/null | grep -E "(News Delivery|main.py|backup_data)" || echo "No News Delivery cron jobs found"
    
    echo ""
    echo "🔍 Recent cron executions:"
    
    # Check if log files exist and show recent entries
    LOG_FILES=("cron_morning.log" "cron_noon.log" "cron_evening.log" "cron_backup.log")
    
    for log_file in "${LOG_FILES[@]}"; do
        log_path="$PROJECT_PATH/logs/$log_file"
        if [ -f "$log_path" ]; then
            echo "📄 $log_file (last 3 lines):"
            tail -n 3 "$log_path" | sed 's/^/   /'
            echo ""
        else
            echo "📄 $log_file: No logs yet"
        fi
    done
    
    # Show next scheduled run times
    echo "⏰ Next scheduled executions:"
    echo "   🌅 Next morning run:  $(date -d 'tomorrow 07:00' '+%Y-%m-%d %H:%M')"
    echo "   🌞 Next noon run:     $(date -d 'today 12:00' '+%Y-%m-%d %H:%M' 2>/dev/null || date -d 'tomorrow 12:00' '+%Y-%m-%d %H:%M')"
    echo "   🌆 Next evening run: $(date -d 'today 18:00' '+%Y-%m-%d %H:%M' 2>/dev/null || date -d 'tomorrow 18:00' '+%Y-%m-%d %H:%M')"
}

show_logs() {
    echo "📊 Recent Cron Logs"
    echo "=================="
    
    LOG_FILES=("cron_morning.log" "cron_noon.log" "cron_evening.log" "cron_backup.log")
    
    for log_file in "${LOG_FILES[@]}"; do
        log_path="$PROJECT_PATH/logs/$log_file"
        if [ -f "$log_path" ]; then
            echo ""
            echo "📄 $log_file:"
            echo "─────────────────────────────────────"
            tail -n 10 "$log_path"
        fi
    done
    
    echo ""
    echo "💡 To monitor logs in real-time:"
    echo "   tail -f $PROJECT_PATH/logs/cron_*.log"
}

test_execution() {
    echo "🧪 Testing News Delivery Execution"
    echo "================================="
    
    cd "$PROJECT_PATH"
    
    echo "📍 Current directory: $(pwd)"
    echo "🐍 Python version: $(python3 --version)"
    echo ""
    echo "🚀 Running test execution..."
    
    # Run the main script in test mode
    python3 src/main.py --mode test
    
    echo ""
    echo "✅ Test execution completed!"
}

# Main script logic
case "$1" in
    "install")
        install_cron
        ;;
    "remove")
        remove_cron
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "test")
        test_execution
        ;;
    "help"|"")
        show_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac