#!/bin/bash

# 4-Developer Team Setup with Claude Auth Support
# Manager/CTO Equal + 4 Devs Linear + Claude

SESSION_NAME="team-4devs"
BASE_DIR="/media/kensan/LinuxHDD/news-delivery-system"
TMUX_DIR="$BASE_DIR/tmux"

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up 4-Developer Team with Claude Auth Support...${NC}"

# Kill existing session if it exists
tmux kill-session -t $SESSION_NAME 2>/dev/null

# Create new session
tmux new-session -d -s $SESSION_NAME -c "$BASE_DIR"

# Setup panes for 4-developer linear layout
# Manager/CTO (top-left)
tmux rename-window -t $SESSION_NAME:0 "Team-4Devs"
tmux send-keys -t $SESSION_NAME:0.0 "cd $BASE_DIR" C-m
tmux send-keys -t $SESSION_NAME:0.0 "echo 'Manager/CTO Terminal Ready'" C-m

# Developer 1 (top-right)
tmux split-window -t $SESSION_NAME:0 -h -p 50
tmux send-keys -t $SESSION_NAME:0.1 "cd $BASE_DIR" C-m
tmux send-keys -t $SESSION_NAME:0.1 "echo 'Developer 1 Terminal Ready'" C-m

# Developer 2 (middle-left)
tmux split-window -t $SESSION_NAME:0.0 -v -p 66
tmux send-keys -t $SESSION_NAME:0.2 "cd $BASE_DIR" C-m
tmux send-keys -t $SESSION_NAME:0.2 "echo 'Developer 2 Terminal Ready'" C-m

# Developer 3 (middle-right)
tmux split-window -t $SESSION_NAME:0.1 -v -p 66
tmux send-keys -t $SESSION_NAME:0.3 "cd $BASE_DIR" C-m
tmux send-keys -t $SESSION_NAME:0.3 "echo 'Developer 3 Terminal Ready'" C-m

# Developer 4 (bottom-left)
tmux split-window -t $SESSION_NAME:0.2 -v -p 50
tmux send-keys -t $SESSION_NAME:0.4 "cd $BASE_DIR" C-m
tmux send-keys -t $SESSION_NAME:0.4 "echo 'Developer 4 Terminal Ready'" C-m

# Claude with authentication support (bottom-right)
tmux split-window -t $SESSION_NAME:0.3 -v -p 50
tmux send-keys -t $SESSION_NAME:0.5 "cd $BASE_DIR" C-m

# Start Claude with --dangerously-skip-permissions for auth testing
echo -e "${YELLOW}Starting Claude with --dangerously-skip-permissions...${NC}"
tmux send-keys -t $SESSION_NAME:0.5 "claude --dangerously-skip-permissions" C-m

# Set pane titles
tmux select-pane -t $SESSION_NAME:0.0 -T "Manager/CTO"
tmux select-pane -t $SESSION_NAME:0.1 -T "Developer-1"
tmux select-pane -t $SESSION_NAME:0.2 -T "Developer-2"
tmux select-pane -t $SESSION_NAME:0.3 -T "Developer-3"
tmux select-pane -t $SESSION_NAME:0.4 -T "Developer-4"
tmux select-pane -t $SESSION_NAME:0.5 -T "Claude-AI"

# Create communication window
tmux new-window -t $SESSION_NAME:1 -n "Communication"
tmux send-keys -t $SESSION_NAME:1 "cd $TMUX_DIR" C-m
tmux send-keys -t $SESSION_NAME:1 "echo 'Team Communication Hub Ready'" C-m

# Create monitoring window
tmux new-window -t $SESSION_NAME:2 -n "Monitor"
tmux send-keys -t $SESSION_NAME:2 "cd $BASE_DIR" C-m
tmux send-keys -t $SESSION_NAME:2 "echo 'System Monitor Ready'" C-m

# Create project management window
tmux new-window -t $SESSION_NAME:3 -n "Project"
tmux send-keys -t $SESSION_NAME:3 "cd $BASE_DIR" C-m
tmux send-keys -t $SESSION_NAME:3 "echo 'Project Management Ready'" C-m

# Select main window and focus on Manager pane
tmux select-window -t $SESSION_NAME:0
tmux select-pane -t $SESSION_NAME:0.0

echo -e "${GREEN}4-Developer Team setup complete!${NC}"
echo -e "${BLUE}Session: $SESSION_NAME${NC}"
echo -e "${BLUE}Attach with: tmux attach-session -t $SESSION_NAME${NC}"
echo -e "${YELLOW}Claude started with --dangerously-skip-permissions for auth testing${NC}"

# Attach to session
tmux attach-session -t $SESSION_NAME