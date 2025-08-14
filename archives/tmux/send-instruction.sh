#!/bin/bash
TARGET_ROLE="$1"
INSTRUCTION="$2"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# ターゲットペイン特定
case "$TARGET_ROLE" in
    "manager"|"MANAGER") TARGET_PANE="0.0" ;;
    "cto"|"CTO") TARGET_PANE="0.1" ;;
    "dev0"|"DEV0") TARGET_PANE="0.2" ;;
    "dev1"|"DEV1") TARGET_PANE="0.3" ;;
    "dev2"|"DEV2") TARGET_PANE="0.4" ;;
    "dev3"|"DEV3") TARGET_PANE="0.5" ;;
    "dev4"|"DEV4") TARGET_PANE="0.6" ;;
    "dev5"|"DEV5") TARGET_PANE="0.7" ;;
    *) echo "Unknown target role: $TARGET_ROLE"; exit 1 ;;
esac

# 指示をペインに送信
tmux send-keys -t "news-dev-team:$TARGET_PANE" "echo '【$TIMESTAMP】指示受信: $INSTRUCTION'" C-m

echo "Instruction sent to $TARGET_ROLE (pane $TARGET_PANE): $INSTRUCTION"
