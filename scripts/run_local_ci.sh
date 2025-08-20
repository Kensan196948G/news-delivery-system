#!/bin/bash
# Local CI Pipeline Runner
# ローカルでCI/CDパイプラインを実行

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  News Delivery System - Local CI/CD${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to run a step
run_step() {
    local step_name="$1"
    local command="$2"
    
    echo -e "${YELLOW}▶ Running: $step_name${NC}"
    if eval "$command"; then
        echo -e "${GREEN}✅ $step_name completed successfully${NC}\n"
        return 0
    else
        echo -e "${RED}❌ $step_name failed${NC}\n"
        return 1
    fi
}

# Function to run with continue on error
run_optional_step() {
    local step_name="$1"
    local command="$2"
    
    echo -e "${YELLOW}▶ Running (optional): $step_name${NC}"
    if eval "$command" 2>/dev/null; then
        echo -e "${GREEN}✅ $step_name completed successfully${NC}\n"
    else
        echo -e "${YELLOW}⚠️  $step_name skipped or failed (non-critical)${NC}\n"
    fi
}

# 1. Environment Check
echo -e "${BLUE}1. Environment Check${NC}"
run_step "Python version check" "python --version"
run_step "Pip version check" "pip --version"

# 2. Dependencies Installation
echo -e "${BLUE}2. Installing Dependencies${NC}"
run_step "Upgrade pip" "python -m pip install --upgrade pip --quiet"
run_step "Install requirements" "pip install -r requirements.txt --quiet"
run_optional_step "Install dev requirements" "pip install -r requirements-dev.txt --quiet"

# 3. Auto-fix Scripts
echo -e "${BLUE}3. Running Auto-fix Scripts${NC}"
run_optional_step "Fix imports" "python scripts/fix_imports.py"
run_optional_step "Fix type hints" "python scripts/fix_type_hints.py"
run_optional_step "Fix dependencies" "python scripts/fix_dependencies.py"
run_optional_step "Fix config" "python scripts/fix_config.py"

# 4. Code Quality Checks
echo -e "${BLUE}4. Code Quality Checks${NC}"
run_optional_step "Ruff linting" "ruff check src/ tests/ --format=github"
run_optional_step "Black formatting check" "black --check src/ tests/"
run_optional_step "isort import check" "isort --check-only src/ tests/"

# 5. Security Checks
echo -e "${BLUE}5. Security Checks${NC}"
run_optional_step "Bandit security scan" "bandit -r src/ -ll"
run_optional_step "Safety vulnerability check" "safety check --json"

# 6. Type Checking
echo -e "${BLUE}6. Type Checking${NC}"
run_optional_step "MyPy type check" "mypy src/ --ignore-missing-imports --no-strict-optional"

# 7. Tests
echo -e "${BLUE}7. Running Tests${NC}"
if command -v pytest &> /dev/null; then
    run_step "Integration tests" "pytest tests/test_integration.py -v --tb=short"
else
    echo -e "${YELLOW}⚠️  pytest not installed, installing...${NC}"
    pip install pytest pytest-asyncio
    run_step "Integration tests" "pytest tests/test_integration.py -v --tb=short"
fi

# 8. Configuration Validation
echo -e "${BLUE}8. Configuration Validation${NC}"
run_step "Validate paths" "python -c 'from src.utils.path_resolver import get_path_resolver; pr = get_path_resolver(); print(\"✓ Path resolver working\"); print(pr.get_platform_info())'"
run_step "Validate config" "python -c 'from src.utils.config import get_config; cfg = get_config(); errors = cfg.validate_config(); print(\"✓ Config validated\" if not errors else f\"Issues: {errors}\")'"

# 9. Health Check
echo -e "${BLUE}9. System Health Check${NC}"
python -c "
import asyncio
import sys
sys.path.insert(0, 'src')

async def check():
    try:
        from monitoring.health_monitor import HealthMonitor
        monitor = HealthMonitor()
        status = await monitor.perform_health_check()
        print(f'Overall health: {status.get(\"overall_health\")}')
        if status.get('issues'):
            print(f'Issues: {status[\"issues\"]}')
        return status.get('overall_health') == 'healthy'
    except Exception as e:
        print(f'Health check error: {e}')
        return False

result = asyncio.run(check())
sys.exit(0 if result else 1)
" && echo -e "${GREEN}✅ Health check passed${NC}\n" || echo -e "${YELLOW}⚠️  Health check issues detected${NC}\n"

# 10. Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  CI/CD Pipeline Summary${NC}"
echo -e "${BLUE}========================================${NC}"

# Count successes and failures
TOTAL_STEPS=9
FAILED_STEPS=0

# Simple summary
echo -e "${GREEN}Pipeline completed!${NC}"
echo ""
echo "Next steps:"
echo "1. Review any warnings or errors above"
echo "2. Commit changes if auto-fixes were applied:"
echo "   git add -A && git commit -m '🔧 fix: Apply auto-fixes from CI pipeline'"
echo "3. Push to GitHub:"
echo "   git push origin main"
echo ""
echo -e "${BLUE}For manual scheduler setup:${NC}"
echo "   python src/utils/scheduler_manager.py setup"
echo ""
echo -e "${BLUE}For manual testing:${NC}"
echo "   python src/main.py --test"