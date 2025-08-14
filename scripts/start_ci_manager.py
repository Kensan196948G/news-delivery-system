#!/usr/bin/env python3
"""
NEWS-CIManager Agent Startup Script
CI/CDマネージャーエージェント起動スクリプト
"""

import sys
import os
import asyncio
import argparse
from pathlib import Path

# プロジェクトルートを Python パスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from agents.ci_manager import CIPipelineManager

async def start_ci_manager(config_path: str = None, daemon: bool = False):
    """CI Manager エージェント起動"""
    
    # 設定ファイルパスの決定
    if not config_path:
        config_path = str(project_root / "config" / "config.json")
    
    # CI Manager インスタンス作成
    ci_manager = CIPipelineManager(config_path=config_path)
    
    print(f"Starting NEWS-CIManager Agent...")
    print(f"Config path: {config_path}")
    print(f"Daemon mode: {daemon}")
    
    try:
        # エージェント起動
        agent_status = await ci_manager.spawn_agent(
            agent_type="manager",
            name="news-cimanager",
            capabilities=["pipeline-management", "deployment"]
        )
        
        print(f"✅ Agent spawned successfully - Status: {agent_status.status}")
        
        if daemon:
            print("🔄 Running in daemon mode... (Press Ctrl+C to stop)")
            # デーモンモードでの継続実行
            while True:
                # 定期的なヘルスチェック
                health = await ci_manager.monitor_pipeline_health()
                
                # アラートがある場合は出力
                if health.get('alerts'):
                    print(f"⚠️  Alerts detected: {len(health['alerts'])} issues")
                    for alert in health['alerts']:
                        print(f"   - {alert['type']}: {alert['message']}")
                
                # 30秒待機
                await asyncio.sleep(30)
        else:
            # シングル実行モード
            print("📊 Generating dashboard data...")
            dashboard = await ci_manager.generate_ci_dashboard()
            
            print("\n📈 CI Dashboard Summary:")
            print(f"  Total Agents: {dashboard['summary_stats']['total_agents']}")
            print(f"  Success Rate (24h): {dashboard['summary_stats']['success_rate_24h']:.1%}")
            print(f"  Avg Duration (7d): {dashboard['summary_stats']['avg_duration_7d']} min")
            print(f"  Deployments (month): {dashboard['summary_stats']['deployments_this_month']}")
            
            # システム健全性表示
            system_health = dashboard['system_health']
            print(f"\n🏥 System Health: {system_health['overall_status'].upper()}")
            for component, status in system_health['components'].items():
                status_icon = "✅" if status == "healthy" else "⚠️"
                print(f"  {status_icon} {component}: {status}")
            
    except KeyboardInterrupt:
        print("\n🛑 Shutdown signal received...")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    finally:
        print("🔄 Cleaning up...")
        await ci_manager.cleanup()
        print("✅ CI Manager stopped")
    
    return 0

def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description="NEWS-CIManager Agent")
    parser.add_argument(
        "--config", 
        type=str, 
        help="Configuration file path"
    )
    parser.add_argument(
        "--daemon", 
        action="store_true", 
        help="Run in daemon mode"
    )
    parser.add_argument(
        "--test", 
        action="store_true", 
        help="Run test mode with sample data"
    )
    
    args = parser.parse_args()
    
    if args.test:
        print("🧪 Running in test mode...")
        # テストモード用の設定
        args.daemon = False
    
    # 非同期実行
    return asyncio.run(start_ci_manager(
        config_path=args.config,
        daemon=args.daemon
    ))

if __name__ == "__main__":
    sys.exit(main())