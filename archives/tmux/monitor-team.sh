#!/bin/bash
while true; do
    echo "=== $(date '+%H:%M:%S') チーム状態 ==="
    
    # 各ペインの状態表示
    for i in {0..7}; do
        if tmux list-panes -t "news-dev-team:0.$i" 2>/dev/null; then
            title=$(tmux display-message -t "news-dev-team:0.$i" -p '#{pane_title}')
            echo "Pane $i: $title"
        fi
    done
    
    sleep 30
done
