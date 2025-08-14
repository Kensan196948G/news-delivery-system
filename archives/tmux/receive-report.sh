#!/bin/bash
FROM_ROLE="$1"
REPORT="$2"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "【$TIMESTAMP】報告受信 from $FROM_ROLE: $REPORT" >> "$TMUX_DIR/logs/team-reports.log"

# 管理者ペインに通知
tmux send-keys -t "news-dev-team:0.0" "echo '【報告】$FROM_ROLE: $REPORT'" C-m
tmux send-keys -t "news-dev-team:0.1" "echo '【報告】$FROM_ROLE: $REPORT'" C-m

echo "Report received from $FROM_ROLE: $REPORT"
