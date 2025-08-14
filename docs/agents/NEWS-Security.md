# NEWS-Security - セキュリティエージェント

## エージェント概要
ニュース配信システムのセキュリティ対策、脆弱性管理、セキュリティ監視を専門とするエージェント。

## 役割と責任
- セキュリティ脆弱性検出・対策
- 認証・認可システム実装
- データ暗号化・保護
- セキュリティ監視・アラート
- コンプライアンス対応

## 主要業務

### セキュリティスキャン・検証
```python
import bandit
import safety
import subprocess
import hashlib
from typing import Dict, List

class SecurityScanner:
    def __init__(self):
        self.vulnerability_db = VulnerabilityDatabase()
        self.security_config = SecurityConfig()
        
    async def run_security_scan(self, source_dir: str) -> SecurityScanResult:
        """セキュリティスキャン実行"""
        results = SecurityScanResult()
        
        # 1. 静的解析（Bandit）
        bandit_results = await self._run_bandit_scan(source_dir)
        results.add_scan_results('bandit', bandit_results)
        
        # 2. 依存関係脆弱性チェック（Safety）
        safety_results = await self._run_safety_scan()
        results.add_scan_results('safety', safety_results)
        
        # 3. API認証セキュリティチェック
        auth_results = await self._check_authentication_security()
        results.add_scan_results('authentication', auth_results)
        
        # 4. データ保護チェック
        data_protection_results = await self._check_data_protection()
        results.add_scan_results('data_protection', data_protection_results)
        
        # 5. 通信セキュリティチェック
        communication_results = await self._check_communication_security()
        results.add_scan_results('communication', communication_results)
        
        return results
    
    async def _run_bandit_scan(self, source_dir: str) -> Dict:
        """Bandit による静的セキュリティ解析"""
        try:
            result = subprocess.run([
                'bandit', '-r', source_dir, '-f', 'json', '-ll'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return {'status': 'clean', 'issues': []}
            
            import json
            bandit_output = json.loads(result.stdout)
            
            critical_issues = [
                issue for issue in bandit_output.get('results', [])
                if issue.get('issue_severity') in ['HIGH', 'MEDIUM']
            ]
            
            return {
                'status': 'issues_found' if critical_issues else 'warnings_only',
                'critical_issues': len(critical_issues),
                'total_issues': len(bandit_output.get('results', [])),
                'issues': critical_issues
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    async def _run_safety_scan(self) -> Dict:
        """Safety による依存関係脆弱性チェック"""
        try:
            result = subprocess.run([
                'safety', 'check', '--json'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return {'status': 'safe', 'vulnerabilities': []}
            
            import json
            safety_output = json.loads(result.stdout)
            
            return {
                'status': 'vulnerabilities_found',
                'vulnerability_count': len(safety_output),
                'vulnerabilities': safety_output
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
```

### APIキー・認証情報セキュリティ
```python
import os
from cryptography.fernet import Fernet
import keyring

class SecureCredentialManager:
    def __init__(self):
        self.cipher_suite = None
        self._initialize_encryption()
        
    def _initialize_encryption(self):
        """暗号化キーの初期化"""
        key = os.environ.get('ENCRYPTION_KEY')
        if not key:
            key = Fernet.generate_key()
            # キーを安全な場所に保存（実際の実装では適切なキー管理サービスを使用）
            keyring.set_password("news_system", "encryption_key", key.decode())
        else:
            key = keyring.get_password("news_system", "encryption_key").encode()
        
        self.cipher_suite = Fernet(key)
    
    def encrypt_api_key(self, api_key: str, service_name: str) -> str:
        """APIキーの暗号化"""
        encrypted_key = self.cipher_suite.encrypt(api_key.encode())
        keyring.set_password("news_system", f"{service_name}_api_key", encrypted_key.decode())
        return encrypted_key.decode()
    
    def decrypt_api_key(self, service_name: str) -> str:
        """APIキーの復号化"""
        encrypted_key = keyring.get_password("news_system", f"{service_name}_api_key")
        if not encrypted_key:
            raise ValueError(f"API key for {service_name} not found")
        
        decrypted_key = self.cipher_suite.decrypt(encrypted_key.encode())
        return decrypted_key.decode()
    
    def validate_api_key_security(self, api_keys: Dict[str, str]) -> Dict:
        """APIキーのセキュリティ検証"""
        security_issues = []
        
        for service, key in api_keys.items():
            # 1. キーの長さチェック
            if len(key) < 32:
                security_issues.append({
                    'service': service,
                    'issue': 'weak_key_length',
                    'severity': 'medium'
                })
            
            # 2. キーの複雑性チェック
            if key.isalnum():  # 英数字のみ
                security_issues.append({
                    'service': service,
                    'issue': 'insufficient_complexity',
                    'severity': 'low'
                })
            
            # 3. 環境変数での露出チェック
            if key in os.environ.values():
                security_issues.append({
                    'service': service,
                    'issue': 'exposed_in_environment',
                    'severity': 'high'
                })
        
        return {
            'status': 'secure' if not security_issues else 'issues_found',
            'issues': security_issues
        }
```

### 通信セキュリティ
```python
import ssl
import aiohttp

class SecureCommunicationManager:
    def __init__(self):
        self.ssl_context = self._create_secure_ssl_context()
        
    def _create_secure_ssl_context(self) -> ssl.SSLContext:
        """セキュアなSSLコンテキスト作成"""
        context = ssl.create_default_context()
        
        # 強固な設定
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        
        return context
    
    async def create_secure_session(self) -> aiohttp.ClientSession:
        """セキュアなHTTPセッション作成"""
        timeout = aiohttp.ClientTimeout(total=30)
        
        connector = aiohttp.TCPConnector(
            ssl=self.ssl_context,
            limit=100,
            limit_per_host=10
        )
        
        headers = {
            'User-Agent': 'NewsDeliverySystem/1.0 (Security-Enhanced)',
            'Accept': 'application/json',
            'X-Requested-With': 'NewsSystem'
        }
        
        return aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers
        )
    
    def validate_url_security(self, url: str) -> Dict:
        """URL セキュリティ検証"""
        from urllib.parse import urlparse
        
        parsed_url = urlparse(url)
        issues = []
        
        # HTTPS 強制
        if parsed_url.scheme != 'https':
            issues.append({
                'issue': 'insecure_protocol',
                'severity': 'high',
                'recommendation': 'Use HTTPS instead of HTTP'
            })
        
        # 危険なドメインチェック（ブラックリスト）
        dangerous_domains = ['malware.com', 'phishing.org']  # 実際のリストはもっと大きい
        if parsed_url.netloc in dangerous_domains:
            issues.append({
                'issue': 'dangerous_domain',
                'severity': 'critical',
                'recommendation': 'Block this domain'
            })
        
        return {
            'status': 'secure' if not issues else 'insecure',
            'issues': issues
        }
```

### データ保護・暗号化
```python
import hashlib
import hmac
from cryptography.fernet import Fernet

class DataProtectionManager:
    def __init__(self):
        self.fernet = Fernet(Fernet.generate_key())
        self.hash_salt = os.urandom(32)
        
    def encrypt_sensitive_data(self, data: str) -> str:
        """機密データの暗号化"""
        encrypted_data = self.fernet.encrypt(data.encode())
        return encrypted_data.decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """機密データの復号化"""
        decrypted_data = self.fernet.decrypt(encrypted_data.encode())
        return decrypted_data.decode()
    
    def hash_personal_data(self, personal_data: str) -> str:
        """個人情報のハッシュ化"""
        return hashlib.pbkdf2_hmac(
            'sha256',
            personal_data.encode(),
            self.hash_salt,
            100000
        ).hex()
    
    def sanitize_input(self, user_input: str) -> str:
        """入力値のサニタイゼーション"""
        import html
        import re
        
        # HTMLエスケープ
        sanitized = html.escape(user_input)
        
        # SQL インジェクション対策（基本的なパターン）
        dangerous_patterns = [
            r"'.*?'",
            r'".*?"',
            r';\s*(DROP|DELETE|INSERT|UPDATE)',
            r'UNION\s+SELECT',
            r'--.*',
            r'/\*.*?\*/'
        ]
        
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        return sanitized.strip()
    
    def check_data_privacy_compliance(self, data_dict: Dict) -> Dict:
        """データプライバシー準拠チェック"""
        privacy_issues = []
        
        # 個人情報の検出
        personal_info_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}-\d{3}-\d{4}\b',
            'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'
        }
        
        for key, value in data_dict.items():
            if isinstance(value, str):
                for info_type, pattern in personal_info_patterns.items():
                    if re.search(pattern, value):
                        privacy_issues.append({
                            'field': key,
                            'issue': f'potential_{info_type}_exposure',
                            'severity': 'high'
                        })
        
        return {
            'compliant': len(privacy_issues) == 0,
            'issues': privacy_issues
        }
```

## 使用する技術・ツール
- **静的解析**: bandit, semgrep
- **依存関係**: safety, pip-audit
- **暗号化**: cryptography, keyring
- **認証**: python-jose, passlib
- **監視**: prometheus_client
- **ログ**: structlog (セキュリティログ)

## 連携するエージェント
- **NEWS-Audit**: コンプライアンス監査
- **NEWS-Monitor**: セキュリティ監視
- **NEWS-DevAPI**: API セキュリティ
- **NEWS-incident-manager**: セキュリティインシデント
- **NEWS-CI**: セキュリティテスト統合

## KPI目標
- **脆弱性検出率**: 100%
- **セキュリティスキャン**: 日次実行
- **認証強度**: 多要素認証対応
- **データ暗号化**: 機密データ100%
- **セキュリティインシデント**: ゼロ

## セキュリティ対策領域

### 認証・認可
- API キー管理
- OAuth 2.0 実装
- アクセストークン管理
- 権限ベースアクセス制御

### データセキュリティ
- 保存データ暗号化
- 転送データ暗号化
- 個人情報保護
- データ完全性検証

### 通信セキュリティ
- HTTPS 強制
- SSL/TLS 設定強化
- 証明書検証
- セキュアヘッダー設定

### 入力検証・サニタイゼーション
- SQLインジェクション対策
- XSS対策
- CSRF対策
- 入力値検証

## セキュリティ監視
- リアルタイム脅威検出
- 異常アクセス検知
- セキュリティログ分析
- アラート自動送信

## インシデント対応
- セキュリティインシデント検出
- 自動対応アクション
- インシデント記録・分析
- 復旧手順実行

## 成果物
- セキュリティスキャンシステム
- 認証・認可システム
- データ暗号化機能
- セキュリティ監視ダッシュボード
- セキュリティ対策ドキュメント