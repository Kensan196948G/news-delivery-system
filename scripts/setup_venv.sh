#!/bin/bash
# Virtual Environment Setup Script
# 仮想環境のセットアップと有効化

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Setting up Virtual Environment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if venv exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists. Activating...${NC}"
else
    echo -e "${GREEN}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${GREEN}Upgrading pip...${NC}"
python -m pip install --upgrade pip

# Install requirements
echo -e "${GREEN}Installing requirements...${NC}"
pip install -r requirements.txt

# Install dev requirements if exists
if [ -f "requirements-dev.txt" ]; then
    echo -e "${GREEN}Installing dev requirements...${NC}"
    pip install -r requirements-dev.txt
fi

# Install pytest for testing
echo -e "${GREEN}Installing test dependencies...${NC}"
pip install pytest pytest-asyncio pytest-cov

echo ""
echo -e "${GREEN}✅ Virtual environment setup complete!${NC}"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run the local CI pipeline:"
echo "  ./scripts/run_local_ci.sh"
echo ""
echo "To deactivate the virtual environment:"
echo "  deactivate"