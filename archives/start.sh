#!/bin/bash

# News Delivery System - Quick Start Script
# ニュース自動配信システム - クイックスタートスクリプト

echo "🚀 News Delivery System - Quick Start"
echo "======================================"

# Check if tmux auto-start script exists
if [ -f "tmux/auto-start-servers.sh" ]; then
    echo "Starting with tmux controller..."
    ./tmux/auto-start-servers.sh auto
else
    echo "Starting simple mode..."
    
    # Activate virtual environment
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d "news-env" ]; then
        source news-env/bin/activate
    fi
    
    # Run system status
    python main.py status
fi