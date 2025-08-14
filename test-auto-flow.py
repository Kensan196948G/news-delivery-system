#!/usr/bin/env python3
"""
新仕様自動フローテスト用ファイル
1時間以内検知→自動修復→PR作成→メール通知→Issue完了
"""

import os
import subprocess

def test_auto_detection():
    """
    自動検知テスト用の意図的な問題
    新しい完全自動フローがこれらを検知・修復します
    """
    
    # B602: subprocess_popen_with_shell_equals_true
    user_command = "echo 'test'"
    subprocess.Popen(user_command, shell=True)
    
    # B105: hardcoded_password_string  
    database_password = "test_password_123"
    
    # B108: probable_insecure_usage_of_temp_file
    temp_path = "/tmp/auto_flow_test"
    with open(temp_path, 'w') as f:
        f.write("test data")
    
    print("🧪 自動フローテスト用問題作成完了")
    print("📅 検知予定: 1時間以内（30分おき監視）")
    print("🔄 期待される自動フロー:")
    print("1. 🔍 自動検知 (1時間以内)")
    print("2. 📝 Issue自動作成")  
    print("3. 🔧 自動修復実行")
    print("4. 📋 PR自動作成")
    print("5. 📧 成功メール通知")
    print("6. 🔄 Issue自動クローズ")

if __name__ == "__main__":
    test_auto_detection()