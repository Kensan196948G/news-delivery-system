#!/bin/bash

# Terminal Size Helper - ターミナルサイズ最適化ヘルパー

# 色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║              Terminal Size Helper                            ║${NC}"
echo -e "${CYAN}║           6開発者レイアウト対応ガイド                        ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 現在のターミナルサイズ取得
if command -v tmux &> /dev/null && [ -n "$TMUX" ]; then
    TERM_WIDTH=$(tmux display-message -p '#{client_width}')
    TERM_HEIGHT=$(tmux display-message -p '#{client_height}')
    echo -e "${BLUE}現在のターミナルサイズ: ${TERM_WIDTH}x${TERM_HEIGHT}${NC}"
else
    TERM_WIDTH=$(tput cols 2>/dev/null || echo "Unknown")
    TERM_HEIGHT=$(tput lines 2>/dev/null || echo "Unknown")
    echo -e "${BLUE}現在のターミナルサイズ: ${TERM_WIDTH}x${TERM_HEIGHT}${NC}"
fi

echo ""

# 推奨サイズ
echo -e "${CYAN}6開発者レイアウト推奨サイズ:${NC}"
echo "  幅: 120文字以上"
echo "  高さ: 60行以上"
echo ""

# サイズ判定
if [[ "$TERM_WIDTH" != "Unknown" && "$TERM_HEIGHT" != "Unknown" ]]; then
    if [ "$TERM_WIDTH" -ge 120 ] && [ "$TERM_HEIGHT" -ge 60 ]; then
        echo -e "${GREEN}✅ 6開発者レイアウトに適したサイズです${NC}"
    elif [ "$TERM_WIDTH" -ge 100 ] && [ "$TERM_HEIGHT" -ge 40 ]; then
        echo -e "${YELLOW}⚠️ 6開発者レイアウトには少し小さいですが試行可能${NC}"
    else
        echo -e "${RED}❌ 6開発者レイアウトには小さすぎます${NC}"
        echo -e "${CYAN}推奨: 4開発者レイアウトを使用してください${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ ターミナルサイズを検出できませんでした${NC}"
fi

echo ""
echo -e "${CYAN}ターミナルサイズ調整方法:${NC}"
echo ""

# OS別ガイド
case "$(uname -s)" in
    Linux*)
        echo -e "${YELLOW}Linux環境での調整:${NC}"
        echo "1. F11キーでフルスクリーン切り替え"
        echo "2. Ctrl+Shift+Plus でフォントサイズ縮小"
        echo "3. ターミナルウィンドウをドラッグして最大化"
        echo "4. 設定でフォントサイズを調整 (通常8-10pt推奨)"
        ;;
    Darwin*)
        echo -e "${YELLOW}macOS環境での調整:${NC}"
        echo "1. Cmd+Enter でフルスクリーン切り替え"
        echo "2. Cmd+Minus でフォントサイズ縮小"
        echo "3. 緑ボタンでウィンドウ最大化"
        echo "4. 設定でフォントサイズを調整"
        ;;
    *)
        echo -e "${YELLOW}一般的な調整方法:${NC}"
        echo "1. ウィンドウを最大化"
        echo "2. フォントサイズを小さくする"
        echo "3. フルスクリーンモードを使用"
        ;;
esac

echo ""
echo -e "${CYAN}代替案:${NC}"
echo "1. 4開発者レイアウトを使用 (Manager/CTO + 4 Devs)"
echo "2. 外部モニターを使用"
echo "3. ターミナルエミュレーターを変更"
echo "4. SSH経由で大きな画面のサーバーを使用"

echo ""
echo -e "${BLUE}テストコマンド:${NC}"
echo "  ./pane-manager enhanced 4   # 4開発者 (推奨)"
echo "  ./pane-manager enhanced 6   # 6開発者 (サイズ依存)"

echo ""
read -p "Press Enter to close..."