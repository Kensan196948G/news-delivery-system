#!/bin/bash

# Script to cancel all GitHub workflow runs
# This script requires GitHub CLI (gh) to be authenticated

echo "🔄 Cancelling all workflow runs..."

# Function to cancel workflows with pagination
cancel_workflows() {
    local page=1
    local per_page=100
    local cancelled=0
    
    while true; do
        echo "📄 Processing page $page..."
        
        # Get workflow runs for current page
        runs=$(gh run list --limit $per_page --json databaseId,status,conclusion --jq '.[] | select(.status == "in_progress" or .status == "queued") | .databaseId' 2>/dev/null)
        
        if [ -z "$runs" ]; then
            echo "✅ No more active workflow runs found on page $page"
            break
        fi
        
        # Cancel each run
        for run_id in $runs; do
            echo "🛑 Cancelling workflow run $run_id..."
            if gh run cancel $run_id 2>/dev/null; then
                ((cancelled++))
                echo "✅ Cancelled workflow run $run_id"
            else
                echo "❌ Failed to cancel workflow run $run_id"
            fi
        done
        
        ((page++))
        
        # Safety break to prevent infinite loops
        if [ $page -gt 50 ]; then
            echo "⚠️  Reached page limit (50), stopping"
            break
        fi
    done
    
    echo "📊 Total workflow runs cancelled: $cancelled"
}

# Check if gh CLI is authenticated
if ! gh auth status > /dev/null 2>&1; then
    echo "❌ GitHub CLI is not authenticated."
    echo "Please run: gh auth login"
    echo "Then run this script again."
    exit 1
fi

# Cancel all active workflow runs
cancel_workflows

# Alternative approach: Cancel by workflow name
echo ""
echo "🔄 Attempting to cancel workflows by name..."

# Get all workflows and cancel their runs
workflows=$(gh workflow list --json name,id --jq '.[] | .id')

for workflow_id in $workflows; do
    echo "🛑 Cancelling runs for workflow $workflow_id..."
    runs=$(gh run list --workflow=$workflow_id --status=in_progress,queued --json databaseId --jq '.[].databaseId' 2>/dev/null)
    
    for run_id in $runs; do
        gh run cancel $run_id 2>/dev/null && echo "✅ Cancelled run $run_id"
    done
done

echo ""
echo "🎯 Workflow cancellation complete!"
echo "💡 New workflows will start automatically based on the updated .github/workflows/ files"