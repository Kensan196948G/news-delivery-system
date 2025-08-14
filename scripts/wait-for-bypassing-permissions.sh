#!/bin/bash

# Wait for "Bypassing Permissions" to appear in Claude session
# Usage: ./wait-for-bypassing-permissions.sh <session_name> <pane_number>

SESSION_NAME=${1:-"test-session"}
PANE_NUMBER=${2:-"0"}
MAX_WAIT=${3:-30}
CHECK_INTERVAL=1

echo "⏳ Waiting for 'Bypassing Permissions' in session: $SESSION_NAME, pane: $PANE_NUMBER"

for ((i=0; i<MAX_WAIT; i++)); do
    # Capture pane content
    PANE_CONTENT=$(tmux capture-pane -t $SESSION_NAME:$PANE_NUMBER -p 2>/dev/null)
    
    if [[ $? -eq 0 ]]; then
        # Check if "Bypassing Permissions" is present
        if echo "$PANE_CONTENT" | grep -q "Bypassing Permissions"; then
            echo "✅ 'Bypassing Permissions' detected! Authentication complete."
            echo "Time elapsed: ${i} seconds"
            exit 0
        fi
        
        # Show progress every 2 seconds
        if (( i % 2 == 0 )); then
            echo "🔄 Still waiting... (${i}s elapsed)"
        fi
    else
        echo "❌ Session $SESSION_NAME:$PANE_NUMBER not found"
        exit 1
    fi
    
    sleep $CHECK_INTERVAL
done

echo "⚠️ Timeout: 'Bypassing Permissions' not detected within ${MAX_WAIT} seconds"
exit 1