# Claude Authentication Team Guide

## Overview

This guide covers Claude authentication setup for different team configurations using the `--dangerously-skip-permissions` option.

## Team Configurations

### 1. 2-Developer Team (Linear Layout)
- **Structure**: Manager/CTO + 2 Developers + Claude
- **Script**: `./scripts/setup_2devs_claude_auth.sh`
- **Layout**: Linear arrangement with Claude at bottom

### 2. 4-Developer Team (Linear Layout)  
- **Structure**: Manager/CTO + 4 Developers + Claude
- **Script**: `./scripts/setup_4devs_claude_auth.sh`
- **Layout**: 2x3 grid with Claude at bottom-right

### 3. 6-Developer Team (Grid Layout)
- **Structure**: Manager/CTO + 6 Developers + Claude  
- **Script**: `./scripts/setup_6devs_claude_auth.sh`
- **Layout**: 3x3 grid with optimized pane distribution

## Authentication Configuration

### --dangerously-skip-permissions Option

All team scripts use `claude --dangerously-skip-permissions` which:
- Bypasses all permission checks
- Maintains authentication functionality
- Recommended for sandboxed environments only
- Does not affect OAuth or token management

### Test Results

✅ **All configurations tested successfully**
- Claude v1.0.51 compatibility confirmed
- Authentication status accessible
- OAuth flows remain functional
- Gmail integration unaffected

## Usage Instructions

### Quick Start
```bash
# 2-Developer Team
./scripts/setup_2devs_claude_auth.sh

# 4-Developer Team  
./scripts/setup_4devs_claude_auth.sh

# 6-Developer Team
./scripts/setup_6devs_claude_auth.sh
```

### Testing Authentication
```bash
./scripts/test_claude_auth_teams.sh
```

## Security Considerations

⚠️ **Important Notes**:
- `--dangerously-skip-permissions` should only be used in controlled environments
- Authentication mechanisms remain secure
- OAuth tokens and refresh processes are unaffected
- Suitable for development and testing environments

## Troubleshooting

### Common Issues
1. **Timeout errors**: Authentication checks may timeout but functionality remains
2. **Permission warnings**: Expected when using skip-permissions flag
3. **Session conflicts**: Kill existing tmux sessions before starting new ones

### Resolution Steps
1. Verify Claude installation: `claude --version`
2. Test basic functionality: `claude --help`
3. Check authentication: `claude auth status`
4. Use dangerous option: `claude --dangerously-skip-permissions`

## Team Communication

Each setup includes:
- Dedicated communication windows
- Monitoring capabilities  
- Project management panes
- Coordination hubs (6-dev teams)

## Support

For issues or questions:
- Check logs in `tmux/logs/`
- Review authentication status
- Test with provided scripts
- Verify tmux session state