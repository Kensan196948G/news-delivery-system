# 🤝 コントリビューションガイド

## 📋 **貢献方法**

ニュース配信システムの改善にご協力いただき、ありがとうございます！

### **貢献の種類**
- 🐛 **バグ報告**: Issue作成
- ✨ **機能要求**: Feature Request Issue
- 📝 **ドキュメント改善**: Documentation PR
- 🔒 **セキュリティ**: Security Issue
- 💡 **改善提案**: Enhancement Issue

## 🚀 **開発フロー**

### **1. Issue作成**
- 適切なテンプレートを選択
- 詳細な説明を記載
- ラベルが自動付与されます

### **2. 開発準備**
```bash
# リポジトリフォーク
git clone https://github.com/YOUR_USERNAME/news-delivery-system.git
cd news-delivery-system

# 開発環境セットアップ
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

### **3. ブランチ作成**
```bash
# 機能追加
git checkout -b feature/your-feature-name

# バグ修正
git checkout -b bugfix/issue-description

# ドキュメント
git checkout -b docs/documentation-improvement
```

### **4. 開発・テスト**
```bash
# テスト実行
pytest tests/

# コード品質チェック
flake8 src/
mypy src/

# セキュリティチェック
bandit -r src/
safety check
```

### **5. PR作成**
- わかりやすいタイトル
- 変更内容の詳細説明
- 関連Issueの参照
- テスト結果の記載

## 📝 **コーディング規約**

### **Python スタイル**
- **PEP 8** 準拠
- **Type hints** 必須
- **Docstrings** 必須（Google形式）
- **最大行長**: 88文字

### **コミットメッセージ**
```
type(scope): brief description

詳細な説明（必要に応じて）

- 変更点1
- 変更点2

Fixes #123
```

**Type例:**
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント
- `style`: フォーマット
- `refactor`: リファクタリング
- `test`: テスト
- `chore`: その他

## 🧪 **テストガイドライン**

### **必須テスト**
- 新機能には単体テスト必須
- 既存テストの通過確認
- カバレッジ80%以上維持

### **テスト実行**
```bash
# 全テスト実行
pytest

# カバレッジ付き
pytest --cov=src --cov-report=html

# 特定テスト
pytest tests/test_collectors.py
```

## 📚 **ドキュメント**

### **更新が必要な場合**
- API変更時
- 新機能追加時
- 設定項目追加時
- セキュリティ関連変更時

### **ドキュメント形式**
- **Markdown** 使用
- **日本語** 優先
- **コード例** 含める
- **スクリーンショット** 必要に応じて

## 🔒 **セキュリティ**

### **脆弱性報告**
- Security Issueテンプレート使用
- 機密情報は含めない
- 影響範囲を明記

### **セキュアコーディング**
- 入力検証の実装
- 機密情報のログ出力禁止
- 適切な権限設定
- 依存関係の定期更新

## 📞 **サポート**

### **質問・相談**
- GitHub Discussions
- Issue（質問ラベル）

### **緊急時**
- Security Issue作成
- kensan1969@gmail.com へ連絡

---

**🎯 皆様のご協力により、より良いシステムを構築できます！**