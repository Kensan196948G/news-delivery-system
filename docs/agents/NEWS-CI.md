# NEWS-CI - CI/CD運用エージェント

## エージェント概要
ニュース配信システムの継続的インテグレーション（CI）・継続的デリバリー（CD）の運用を専門とするエージェント。

## 役割と責任
- CI/CDパイプライン設計・実装
- 自動テスト実行管理
- デプロイメント自動化
- 品質ゲート管理
- リリース管理

## 主要業務

### CI/CDパイプライン設計
```yaml
# .github/workflows/news-delivery-ci.yml
name: News Delivery System CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '18'

jobs:
  code-quality:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
        
    - name: Code formatting check (Black)
      run: black --check src/
      
    - name: Import sorting check (isort)
      run: isort --check-only src/
      
    - name: Linting (flake8)
      run: flake8 src/
      
    - name: Type checking (mypy)
      run: mypy src/
      
    - name: Security scanning (bandit)
      run: bandit -r src/
      
    - name: Dependency vulnerability check (safety)
      run: safety check --json
      
  unit-tests:
    runs-on: ubuntu-latest
    needs: code-quality
    
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
        
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
        
    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=src/ --cov-report=xml --cov-report=html
        
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        
  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    services:
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
          
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
        
    - name: Run integration tests
      env:
        REDIS_URL: redis://localhost:6379
        TEST_DATABASE_URL: sqlite:///test.db
      run: |
        pytest tests/integration/ -v --tb=short
        
  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
        
    - name: Start application
      run: |
        python src/main.py &
        sleep 30  # Wait for application to start
        
    - name: Run E2E tests
      env:
        E2E_BASE_URL: http://localhost:8000
      run: |
        pytest tests/e2e/ -v --tb=short
        
  build-and-publish:
    runs-on: ubuntu-latest
    needs: [code-quality, unit-tests, integration-tests, e2e-tests]
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        
    - name: Build distribution packages
      run: |
        python -m pip install --upgrade pip build
        python -m build
        
    - name: Create deployment package
      run: |
        mkdir -p deploy/
        cp -r src/ deploy/
        cp requirements.txt deploy/
        cp config/ deploy/ -r
        cp templates/ deploy/ -r
        zip -r news-delivery-system.zip deploy/
        
    - name: Upload deployment artifact
      uses: actions/upload-artifact@v3
      with:
        name: deployment-package
        path: news-delivery-system.zip
        
  deploy-staging:
    runs-on: ubuntu-latest
    needs: build-and-publish
    if: github.ref == 'refs/heads/main'
    environment: staging
    
    steps:
    - name: Download deployment artifact
      uses: actions/download-artifact@v3
      with:
        name: deployment-package
        
    - name: Deploy to staging
      run: |
        # ステージング環境へのデプロイスクリプト実行
        echo "Deploying to staging environment..."
        # 実際の実装では、リモートサーバーへのデプロイ処理
        
    - name: Run smoke tests
      run: |
        # ステージング環境でのスモークテスト
        echo "Running smoke tests on staging..."
        
  deploy-production:
    runs-on: ubuntu-latest
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
    - name: Download deployment artifact
      uses: actions/download-artifact@v3
      with:
        name: deployment-package
        
    - name: Deploy to production
      run: |
        # 本番環境へのデプロイスクリプト実行
        echo "Deploying to production environment..."
        # 実際の実装では、リモートサーバーへのデプロイ処理
        
    - name: Post-deployment verification
      run: |
        # 本番デプロイ後の検証
        echo "Verifying production deployment..."
```

### 自動品質ゲート管理
```python
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class QualityGate:
    name: str
    threshold: float
    current_value: float
    passed: bool
    critical: bool

class QualityGateManager:
    def __init__(self):
        self.quality_thresholds = {
            'code_coverage': {'min': 90.0, 'critical': True},
            'test_success_rate': {'min': 95.0, 'critical': True},
            'security_issues': {'max': 0, 'critical': True},
            'code_quality_score': {'min': 8.0, 'critical': False},
            'performance_regression': {'max': 5.0, 'critical': False},
            'accessibility_score': {'min': 85.0, 'critical': False}
        }
        
    async def evaluate_quality_gates(self, metrics: Dict) -> Dict:
        """品質ゲート評価"""
        gate_results = []
        overall_passed = True
        critical_failed = False
        
        for metric_name, threshold_config in self.quality_thresholds.items():
            current_value = metrics.get(metric_name, 0)
            
            if 'min' in threshold_config:
                passed = current_value >= threshold_config['min']
            else:  # 'max' threshold
                passed = current_value <= threshold_config['max']
            
            gate = QualityGate(
                name=metric_name,
                threshold=threshold_config.get('min', threshold_config.get('max')),
                current_value=current_value,
                passed=passed,
                critical=threshold_config.get('critical', False)
            )
            
            gate_results.append(gate)
            
            if not passed:
                overall_passed = False
                if gate.critical:
                    critical_failed = True
        
        return {
            'overall_passed': overall_passed,
            'critical_failed': critical_failed,
            'gate_results': gate_results,
            'deployment_approved': overall_passed and not critical_failed
        }
    
    def generate_quality_report(self, gate_evaluation: Dict) -> str:
        """品質レポート生成"""
        report = f"""
# 品質ゲート評価レポート

## 総合結果
- **全体評価**: {'✅ 合格' if gate_evaluation['overall_passed'] else '❌ 不合格'}
- **クリティカル問題**: {'❌ あり' if gate_evaluation['critical_failed'] else '✅ なし'}
- **デプロイ承認**: {'✅ 承認' if gate_evaluation['deployment_approved'] else '❌ 却下'}

## 詳細結果
"""
        
        for gate in gate_evaluation['gate_results']:
            status_icon = '✅' if gate.passed else '❌'
            critical_marker = ' (Critical)' if gate.critical else ''
            
            report += f"- **{gate.name}**: {status_icon} {gate.current_value} (閾値: {gate.threshold}){critical_marker}\n"
        
        if not gate_evaluation['deployment_approved']:
            report += "\n## 必要な改善アクション\n"
            failed_gates = [g for g in gate_evaluation['gate_results'] if not g.passed]
            for gate in failed_gates:
                report += f"- {gate.name}: {gate.current_value} → {gate.threshold} 以上に改善が必要\n"
        
        return report
```

### デプロイメント自動化
```python
import subprocess
import os
from pathlib import Path

class DeploymentManager:
    def __init__(self):
        self.deployment_environments = {
            'staging': {
                'host': 'staging.newsdelivery.local',
                'path': '/opt/news-delivery-staging',
                'service': 'news-delivery-staging'
            },
            'production': {
                'host': 'prod.newsdelivery.local',
                'path': '/opt/news-delivery-prod',
                'service': 'news-delivery-prod'
            }
        }
        
    async def deploy_to_environment(self, environment: str, deployment_package: str) -> Dict:
        """環境別デプロイメント実行"""
        env_config = self.deployment_environments.get(environment)
        if not env_config:
            raise ValueError(f"Unknown environment: {environment}")
            
        deployment_steps = [
            self._backup_current_version,
            self._stop_application,
            self._deploy_new_version,
            self._update_configuration,
            self._run_database_migrations,
            self._start_application,
            self._verify_deployment,
            self._cleanup_old_versions
        ]
        
        deployment_result = {
            'environment': environment,
            'status': 'in_progress',
            'steps_completed': 0,
            'total_steps': len(deployment_steps),
            'errors': []
        }
        
        try:
            for step_func in deployment_steps:
                await step_func(env_config, deployment_package)
                deployment_result['steps_completed'] += 1
                
            deployment_result['status'] = 'success'
            
        except Exception as e:
            deployment_result['status'] = 'failed'
            deployment_result['errors'].append(str(e))
            
            # ロールバック実行
            await self._rollback_deployment(env_config, deployment_result)
            
        return deployment_result
    
    async def _backup_current_version(self, env_config: Dict, package_path: str):
        """現在のバージョンをバックアップ"""
        backup_dir = f"{env_config['path']}_backup_{int(time.time())}"
        subprocess.run(['cp', '-r', env_config['path'], backup_dir], check=True)
        
    async def _deploy_new_version(self, env_config: Dict, package_path: str):
        """新バージョンのデプロイ"""
        # 古いファイルを削除
        subprocess.run(['rm', '-rf', f"{env_config['path']}/*"], shell=True)
        
        # 新しいファイルを展開
        subprocess.run([
            'unzip', '-q', package_path, '-d', env_config['path']
        ], check=True)
        
        # パーミッション設定
        subprocess.run(['chmod', '+x', f"{env_config['path']}/src/main.py"], check=True)
        
    async def _run_database_migrations(self, env_config: Dict, package_path: str):
        """データベースマイグレーション実行"""
        migration_script = f"{env_config['path']}/scripts/migrate.py"
        if Path(migration_script).exists():
            subprocess.run(['python', migration_script], check=True, 
                         cwd=env_config['path'])
    
    async def _verify_deployment(self, env_config: Dict, package_path: str):
        """デプロイメント検証"""
        # ヘルスチェックエンドポイントの確認
        health_check_url = f"http://{env_config['host']}/health"
        
        for attempt in range(30):  # 5分間リトライ
            try:
                response = requests.get(health_check_url, timeout=10)
                if response.status_code == 200:
                    return True
            except requests.RequestException:
                pass
            
            await asyncio.sleep(10)
        
        raise Exception("Health check failed after deployment")
```

### リリース管理
```python
class ReleaseManager:
    def __init__(self):
        self.version_control = VersionControl()
        self.changelog_generator = ChangelogGenerator()
        
    async def create_release(self, version: str, release_notes: str) -> Dict:
        """リリース作成"""
        release_info = {
            'version': version,
            'release_date': datetime.now().isoformat(),
            'release_notes': release_notes,
            'artifacts': [],
            'deployment_status': {}
        }
        
        # リリースタグ作成
        await self._create_release_tag(version)
        
        # リリースアーティファクト作成
        artifacts = await self._create_release_artifacts(version)
        release_info['artifacts'] = artifacts
        
        # チェンジログ更新
        await self._update_changelog(version, release_notes)
        
        # リリース通知
        await self._send_release_notification(release_info)
        
        return release_info
    
    async def _create_release_tag(self, version: str):
        """リリースタグ作成"""
        subprocess.run(['git', 'tag', '-a', f'v{version}', '-m', f'Release {version}'], check=True)
        subprocess.run(['git', 'push', 'origin', f'v{version}'], check=True)
    
    def generate_semantic_version(self, current_version: str, change_type: str) -> str:
        """セマンティックバージョニング"""
        major, minor, patch = map(int, current_version.split('.'))
        
        if change_type == 'major':
            return f"{major + 1}.0.0"
        elif change_type == 'minor':
            return f"{major}.{minor + 1}.0"
        elif change_type == 'patch':
            return f"{major}.{minor}.{patch + 1}"
        else:
            raise ValueError(f"Invalid change type: {change_type}")
```

## 使用する技術・ツール
- **CI/CD**: GitHub Actions, GitLab CI, Jenkins
- **コンテナ**: Docker, Docker Compose
- **テスト**: pytest, coverage.py, tox
- **品質**: SonarQube, CodeClimate
- **デプロイ**: Ansible, Fabric
- **監視**: Prometheus, Grafana

## 連携するエージェント
- **NEWS-Tester**: テスト実行統合
- **NEWS-QA**: 品質ゲート設定
- **NEWS-Security**: セキュリティテスト統合
- **NEWS-Monitor**: デプロイ後監視
- **NEWS-CIManager**: CI/CD管理統括

## KPI目標
- **デプロイ頻度**: 週2回以上
- **デプロイ成功率**: 98%以上
- **MTTR**: 30分以内
- **パイプライン実行時間**: 15分以内
- **品質ゲート通過率**: 95%以上

## パイプライン段階

### 継続的インテグレーション
- コード品質チェック
- 自動テスト実行
- セキュリティスキャン
- カバレッジ測定

### 継続的デリバリー
- アーティファクトビルド
- ステージング展開
- 受け入れテスト
- 本番デプロイ承認

### 継続的デプロイメント
- 自動本番展開
- ヘルスチェック
- ロールバック機能
- デプロイ通知

## 品質管理
- 品質ゲート設定
- メトリクス収集
- トレンド分析
- 改善提案

## リリース管理
- セマンティックバージョニング
- チェンジログ生成
- リリースノート作成
- タグ管理

## 成果物
- CI/CDパイプライン
- デプロイメントスクリプト
- 品質ゲートシステム
- リリース管理ツール
- 運用監視ダッシュボード