# ⏰ News Delivery System - 配信スケジュール詳細

## 📅 **配信スケジュール概要**

**News Delivery System** は Linux Cron を使用して、毎日3回の定期配信と緊急時の即座配信を自動実行します。

---

## 🕰️ **定期配信スケジュール**

### **朝のニュース配信** 🌅
```
実行時刻: 毎日 07:00 (JST)
Cron設定: 0 7 * * *
配信先: kensan1969@gmail.com
処理時間: 約5-8分
```

**配信内容**
- **対象期間**: 前日夜間～当日朝の最新ニュース
- **記事構成**: 全カテゴリ88記事
- **特徴**: 1日のスタートに必要な重要情報
- **件名**: `📰 ニュース配信レポート - 2025年08月08日 🌅 朝刊`

**収集データ**
- 国内社会: 夜間発生の社会ニュース
- 国際社会: 時差を活用した海外夜間ニュース
- 経済: アジア市場開始前の情報
- 技術: 米国時間夜間リリース情報
- セキュリティ: 夜間発見の脆弱性情報

---

### **昼のニュース配信** 🌞
```
実行時刻: 毎日 12:00 (JST)
Cron設定: 0 12 * * *
配信先: kensan1969@gmail.com
処理時間: 約5-8分
```

**配信内容**
- **対象期間**: 朝7時～昼12時の最新ニュース
- **記事構成**: 全カテゴリ88記事（朝との重複は自動除去）
- **特徴**: ランチタイム情報収集・市場動向
- **件名**: `📰 ニュース配信レポート - 2025年08月08日 🌞 昼刊`

**重点情報**
- 市場開始後の経済動向
- 午前中の政治・社会動向
- リアルタイムの国際情勢
- 技術系リリース・アップデート
- 新規セキュリティアラート

---

### **夕方のニュース配信** 🌆
```
実行時刻: 毎日 18:00 (JST)  
Cron設定: 0 18 * * *
配信先: kensan1969@gmail.com
処理時間: 約5-8分
```

**配信内容**
- **対象期間**: 昼12時～夕18時の最新ニュース
- **記事構成**: 全カテゴリ88記事
- **特徴**: 1日の総括・重要ニュースの整理
- **件名**: `📰 ニュース配信レポート - 2025年08月08日 🌆 夕刊`

**総括情報**
- 1日の重要ニュース総括
- 市場終了後の経済総括  
- 夕方発表の政府・企業発表
- 海外朝～昼の主要ニュース
- 1日のセキュリティ動向まとめ

---

## 🚨 **緊急配信システム**

### **緊急配信トリガー条件**

**1. 重大ニュース（重要度10/10）**
```
判定基準: Claude AI分析で重要度スコア10
配信遅延: 記事発見から30分以内
件名例: 🚨 緊急ニュース - 重大事件発生
```

**2. 重大セキュリティ脆弱性（CVSS 9.0+）**
```
判定基準: CVSSスコア9.0以上の脆弱性
配信遅延: NVDデータベース更新から60分以内  
件名例: 🚨 緊急セキュリティアラート - Critical脆弱性
```

### **緊急配信の実行**
- **チェック間隔**: 1時間ごと（定期配信時に実行）
- **配信方式**: HTMLメール + PDF添付
- **配信先**: kensan1969@gmail.com
- **特別マーク**: 件名に🚨アイコン、本文に緊急マーク

---

## 🔄 **週次バックアップスケジュール**

### **データバックアップ** 🗄️
```
実行時刻: 毎週日曜日 23:00 (JST)
Cron設定: 0 23 * * 0
処理内容: データベース・ログ・設定ファイル
保持期間: 12週間（3ヶ月）
```

**バックアップ対象**
- SQLiteデータベース（圧縮）
- 過去30日分のHTMLレポート
- 過去30日分のログファイル
- システム設定ファイル
- バックアップサマリーレポート

---

## 📊 **Cron設定詳細**

### **現在のCrontab設定**
```bash
# News Delivery System - Automated News Collection
# 毎日 7:00, 12:00, 18:00 に実行

# 朝のニュース配信 (7:00)
0 7 * * * cd /media/kensan/LinuxHDD/news-delivery-system && /usr/bin/python3 src/main.py --mode daily >> logs/cron_morning.log 2>&1

# 昼のニュース配信 (12:00)  
0 12 * * * cd /media/kensan/LinuxHDD/news-delivery-system && /usr/bin/python3 src/main.py --mode daily >> logs/cron_noon.log 2>&1

# 夕方のニュース配信 (18:00)
0 18 * * * cd /media/kensan/LinuxHDD/news-delivery-system && /usr/bin/python3 src/main.py --mode daily >> logs/cron_evening.log 2>&1

# 週次バックアップ (日曜日 23:00)
0 23 * * 0 cd /media/kensan/LinuxHDD/news-delivery-system && /usr/bin/python3 scripts/backup_data.py >> logs/cron_backup.log 2>&1
```

### **Cron管理コマンド**
```bash
# 状況確認
./scripts/cron_management.sh status

# ログ確認
./scripts/cron_management.sh logs

# テスト実行
./scripts/cron_management.sh test

# 設定削除
./scripts/cron_management.sh remove

# 再設定
./scripts/cron_management.sh install
```

---

## 🕒 **タイムゾーン・時間設定**

### **基準時間**
- **タイムゾーン**: Asia/Tokyo (JST)
- **夏時間**: 適用なし（日本標準時間）
- **システム時間**: Linux system clock

### **国際的なニュースタイミング**
```
07:00 JST = 22:00 UTC-1 (前日)
12:00 JST = 03:00 UTC (当日)
18:00 JST = 09:00 UTC (当日)
```

**世界時間との関係**
- **米国東部**: JST - 14時間（夏時間時は-13時間）
- **米国西部**: JST - 17時間（夏時間時は-16時間） 
- **欧州**: JST - 8時間（夏時間時は-7時間）
- **韓国・中国**: JST - 0時間（同一時間帯）

---

## 📈 **配信パフォーマンス**

### **処理時間目安**

| 処理段階 | 所要時間 | 詳細 |
|---------|---------|------|
| **ニュース収集** | 2-3分 | API並行呼び出し |
| **翻訳処理** | 1-2分 | DeepL Pro バッチ処理 |
| **AI分析** | 1-2分 | Claude API 並行処理 |
| **レポート生成** | 0.5分 | HTML/PDF生成 |
| **メール送信** | 0.5分 | Gmail App Password |
| **合計** | **5-8分** | **全体パイプライン** |

### **パフォーマンス監視**
- 各段階の処理時間をログ記録
- 10分を超える場合はアラート
- API応答時間の監視
- エラー率の追跡

---

## 🔍 **実行ログとモニタリング**

### **ログファイル構成**
```
logs/
├── cron_morning.log    # 朝の実行ログ
├── cron_noon.log       # 昼の実行ログ  
├── cron_evening.log    # 夕方の実行ログ
└── cron_backup.log     # バックアップログ
```

### **ログ内容例**
```
2025-08-08 07:00:01 - INFO - Starting news delivery system main workflow
2025-08-08 07:00:05 - INFO - Step 1: Collecting news from multiple sources
2025-08-08 07:02:30 - INFO - Collected 88 total articles
2025-08-08 07:02:31 - INFO - Step 2: Removing duplicate articles
2025-08-08 07:02:45 - INFO - After deduplication: 85 unique articles
2025-08-08 07:02:46 - INFO - Step 3: Translating foreign articles
2025-08-08 07:04:15 - INFO - Step 4: AI analysis and summarization
2025-08-08 07:06:20 - INFO - Step 5: Generating HTML and PDF reports
2025-08-08 07:07:10 - INFO - Step 6: Sending email notifications
2025-08-08 07:07:45 - INFO - Daily report sent successfully to kensan1969@gmail.com
2025-08-08 07:07:50 - INFO - News delivery system completed successfully in 470.2 seconds
```

### **監視項目**
- 実行成功・失敗の記録
- 処理時間の記録
- 収集記事数の記録
- API使用量の記録
- エラー内容の記録

---

## 🛠️ **トラブルシューティング**

### **よくある問題と対処法**

**1. メール送信失敗**
```bash
# Gmail認証確認
python3 -c "import os; print('Gmail auth:', 'OK' if os.environ.get('GMAIL_APP_PASSWORD') else 'NG')"

# 手動メール送信テスト
python3 test_gnews_simple.py
```

**2. API制限エラー**
```bash
# API使用量確認
./scripts/cron_management.sh status

# キャッシュクリア
rm -rf data/cache/api_cache/*
```

**3. Cron実行失敗**
```bash
# Cronサービス確認
sudo systemctl status cron

# 手動実行テスト
python3 src/main.py --mode daily
```

### **緊急時対応**
1. **システム一時停止**: `./scripts/cron_management.sh remove`
2. **手動実行**: `python3 src/main.py --mode daily`
3. **ログ確認**: `tail -f logs/cron_*.log`
4. **システム復旧**: `./scripts/cron_management.sh install`

---

## 📞 **システム連絡・通知**

### **配信成功時**
- ログファイルに成功記録
- 配信先（kensan1969@gmail.com）にメール送信
- データベースに配信履歴記録

### **配信失敗時**
- エラーログに詳細記録  
- 3回まで自動リトライ
- 最終失敗時にアラートメール送信

### **システム状態通知**
- 週次バックアップ完了通知
- 月次システム状況レポート
- API使用量警告（制限の80%到達時）

---

**🎯 完全自動化された高品質ニュース配信システムにより、kensan1969@gmail.com へ 毎日3回の安定した情報配信を実現しています！**