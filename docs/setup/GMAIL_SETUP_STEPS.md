# 🚀 Gmail認証 - 5分で完了

## 📋 必要な手動作業

Gmail OAuth認証には**ブラウザでの権限許可**が必要です。

---

## ⚡ **超シンプル手順 (5分)**

### 🔗 **Step 1: 認証URLを取得**
```bash
python tools/show_gmail_url.py
```

### 🌐 **Step 2: ブラウザで認証 (3分)**
1. **表示されたURLをコピー**してブラウザで開く
2. **Googleアカウントでログイン**
3. **「許可」をクリック** (Gmail送信権限)
4. **認証コードをコピー** (例: `4/0AanU0Vj...`)

### 🔑 **Step 3: 認証コードを入力 (1分)**
```bash
python tools/simple_gmail_auth.py
```
認証コードを貼り付けてEnter

### ✅ **完了確認**
```
✅ 認証成功！
📄 token.json ファイルが作成されました
📧 認証アカウント: your-email@gmail.com
✅ Gmail API接続成功
```

---

## 🎯 **認証で許可する権限**

- ✅ **メール送信のみ** (`gmail.send`)
- ❌ メール読み取りなし
- ❌ メールボックスアクセスなし
- ❌ 個人情報アクセスなし

**完全に安全な送信専用権限です。**

---

## 🧪 **認証後のテスト**

### **即座テスト**
```bash
python tools/test_email_delivery.py
```

### **自動配信開始**  
```bash
python tools/run_scheduler.py
```

---

## 🆘 **よくある質問**

### **Q1: 認証URLが長すぎる**
**A**: `tools/show_gmail_url.py`で正確なURLが表示されます

### **Q2: 認証コードが表示されない**
**A**: 
- ブラウザのアドブロッカーを無効化
- シークレットモードで再試行

### **Q3: "invalid_grant" エラー**
**A**: 認証コードの期限切れ。新しいコードを取得

### **Q4: WSLでブラウザが開けない**
**A**: WindowsのブラウザでURLを開けばOK

---

## 📊 **手動作業が必要な理由**

1. **セキュリティ**: OAuth2は対話的認証が必須
2. **権限確認**: ユーザーが権限を明示的に許可する必要
3. **Google仕様**: 自動化された認証は禁止

**これは一度だけの作業です。**

---

## 🎉 **認証完了後の効果**

✅ **完全自動メール配信**
✅ **毎日7:00自動ニュース配信**
✅ **緊急セキュリティアラート**
✅ **HTML/PDFレポート添付**
✅ **100%無人運用**

**🚀 ニュース配信システムが完全稼働します！**

---

## 🔄 **手順まとめ**

```bash
# Step 1: URL表示
python tools/show_gmail_url.py

# Step 2: ブラウザで認証 (手動)
# ↳ URLを開く → ログイン → 許可 → コードコピー

# Step 3: コード入力
python tools/simple_gmail_auth.py

# Step 4: テスト
python tools/test_email_delivery.py

# Step 5: 運用開始
python tools/run_scheduler.py
```

**⏱️ 総時間: 約5分で完全自動化システム稼働開始！**