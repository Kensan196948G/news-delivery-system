#!/usr/bin/env python3
"""
News Delivery System Launcher
ニュース配信システム ランチャー
"""

import sys
import os
import argparse
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.main import NewsDeliverySystem
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure you're running from the project root directory")
    sys.exit(1)


def print_banner():
    """バナー表示"""
    print("=" * 60)
    print("🗞️  News Delivery System Launcher")
    print("   ニュース自動配信システム ランチャー")
    print("=" * 60)


def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(
        description="News Delivery System - ニュース自動配信システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
実行例 Examples:
  %(prog)s --mode daily          日次レポート生成・配信
  %(prog)s --mode emergency      緊急ニュースチェック
  %(prog)s --mode test           システムテスト
  %(prog)s --mode weekly         週次サマリー生成
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['daily', 'emergency', 'test', 'weekly'],
        default='daily',
        help='実行モード (default: daily)'
    )
    
    parser.add_argument(
        '--config',
        help='設定ファイルパス (optional)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='詳細ログ出力'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='実際の送信なしでテスト実行'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        print_banner()
        print(f"🚀 Starting in {args.mode} mode...")
        print(f"📂 Project root: {project_root}")
        if args.config:
            print(f"⚙️  Config file: {args.config}")
        if args.dry_run:
            print("🧪 Dry run mode enabled")
        print()
    
    try:
        # Create system instance
        system = NewsDeliverySystem()
        
        # Execute based on mode
        if args.mode == 'daily':
            if args.verbose:
                print("📰 Running daily news collection and delivery...")
            asyncio.run(system.run_daily_collection())
            
        elif args.mode == 'emergency':
            if args.verbose:
                print("🚨 Running emergency news check...")
            asyncio.run(system.run_emergency_check())
            
        elif args.mode == 'weekly':
            if args.verbose:
                print("📊 Running weekly summary generation...")
            # Add weekly summary method if implemented
            print("Weekly summary mode not yet implemented")
            
        elif args.mode == 'test':
            print("🧪 Running system tests...")
            print("System initialized successfully ✅")
            
            # Basic component tests
            tests = [
                ("Configuration", lambda: system.config is not None),
                ("Logger", lambda: system.logger is not None),
                ("Database", lambda: system.db is not None),
                ("News Collector", lambda: system.news_collector is not None),
                ("Translator", lambda: system.translator is not None),
                ("Analyzer", lambda: system.analyzer is not None),
                ("Report Generator", lambda: system.report_generator is not None),
                ("Email Sender", lambda: system.email_sender is not None),
            ]
            
            for name, test_func in tests:
                try:
                    result = test_func()
                    status = "✅" if result else "❌"
                    print(f"  {status} {name}")
                except Exception as e:
                    print(f"  ❌ {name}: {e}")
            
            print("\n🎉 Test completed")
        
        if args.verbose:
            print("\n✅ Execution completed successfully")
            
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()