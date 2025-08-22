#!/usr/bin/env python3
"""
メトリクスダッシュボードの自動更新
システム統計情報、パフォーマンス履歴、品質メトリクスを管理
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MetricRecord:
    timestamp: str
    metric_type: str
    metric_name: str
    value: float
    details: Dict[str, Any]

class MetricsDashboard:
    def __init__(self, db_path: str = "metrics/metrics.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
        
        # メトリクス保存用ディレクトリ
        self.metrics_dir = Path("metrics")
        self.charts_dir = self.metrics_dir / "charts"
        self.reports_dir = self.metrics_dir / "reports"
        
        for dir_path in [self.metrics_dir, self.charts_dir, self.reports_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def init_database(self):
        """メトリクスデータベースの初期化"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    details TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
                ON metrics(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_type_name 
                ON metrics(metric_type, metric_name)
            """)
    
    def save_metric(self, metric: MetricRecord):
        """メトリクスをデータベースに保存"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO metrics (timestamp, metric_type, metric_name, value, details)
                VALUES (?, ?, ?, ?, ?)
            """, (
                metric.timestamp,
                metric.metric_type,
                metric.metric_name,
                metric.value,
                json.dumps(metric.details)
            ))
    
    def load_test_metrics(self) -> List[MetricRecord]:
        """テストメトリクスファイルから最新データを読み込み"""
        metrics = []
        test_metrics_file = self.metrics_dir / "test-metrics.json"
        
        if test_metrics_file.exists():
            try:
                with open(test_metrics_file) as f:
                    data = json.load(f)
                
                timestamp = data.get('timestamp', datetime.now().isoformat())
                
                # テスト関連メトリクス
                test_metrics_data = [
                    ('test', 'success_rate', data.get('success_rate', 0)),
                    ('test', 'total_tests', data.get('total_tests', 0)),
                    ('test', 'passed_tests', data.get('passed_tests', 0)),
                    ('test', 'failed_tests', data.get('failed_tests', 0)),
                    ('test', 'execution_time', data.get('execution_time', 0)),
                ]
                
                for metric_type, name, value in test_metrics_data:
                    metrics.append(MetricRecord(
                        timestamp=timestamp,
                        metric_type=metric_type,
                        metric_name=name,
                        value=float(value),
                        details=data
                    ))
                
                # カバレッジメトリクス
                coverage = data.get('coverage', {})
                for cov_type, cov_value in coverage.items():
                    if isinstance(cov_value, (int, float)):
                        metrics.append(MetricRecord(
                            timestamp=timestamp,
                            metric_type='coverage',
                            metric_name=cov_type,
                            value=float(cov_value),
                            details=coverage
                        ))
                        
            except Exception as e:
                logger.error(f"Failed to load test metrics: {e}")
        
        return metrics
    
    def load_performance_metrics(self) -> List[MetricRecord]:
        """パフォーマンスメトリクスを読み込み"""
        metrics = []
        
        # ベンチマーク結果ファイルを検索
        benchmark_files = list(self.metrics_dir.glob("benchmark*.json"))
        
        for benchmark_file in benchmark_files:
            try:
                with open(benchmark_file) as f:
                    data = json.load(f)
                
                timestamp = datetime.now().isoformat()
                
                if 'benchmarks' in data:
                    for benchmark in data['benchmarks']:
                        name = benchmark.get('name', 'unknown')
                        stats = benchmark.get('stats', {})
                        
                        for stat_name, stat_value in stats.items():
                            if isinstance(stat_value, (int, float)):
                                metrics.append(MetricRecord(
                                    timestamp=timestamp,
                                    metric_type='performance',
                                    metric_name=f"{name}_{stat_name}",
                                    value=float(stat_value),
                                    details=benchmark
                                ))
                                
            except Exception as e:
                logger.error(f"Failed to load benchmark file {benchmark_file}: {e}")
        
        return metrics
    
    def load_system_metrics(self) -> List[MetricRecord]:
        """システムメトリクスを収集"""
        metrics = []
        timestamp = datetime.now().isoformat()
        
        try:
            # ファイル統計
            src_files = list(Path('src').glob('**/*.py')) if Path('src').exists() else []
            test_files = list(Path('tests').glob('**/*.py')) if Path('tests').exists() else []
            
            total_lines = 0
            for py_file in src_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        lines = len([line for line in f if line.strip() and not line.strip().startswith('#')])
                        total_lines += lines
                except Exception:
                    continue
            
            metrics.extend([
                MetricRecord(timestamp, 'system', 'source_files', len(src_files), {}),
                MetricRecord(timestamp, 'system', 'test_files', len(test_files), {}),
                MetricRecord(timestamp, 'system', 'lines_of_code', total_lines, {}),
            ])
            
            # Git統計
            import subprocess
            try:
                # コミット数
                result = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    commit_count = int(result.stdout.strip())
                    metrics.append(MetricRecord(timestamp, 'git', 'total_commits', commit_count, {}))
                
                # 最近の活動（過去30日のコミット数）
                since_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                result = subprocess.run(['git', 'rev-list', '--count', '--since', since_date, 'HEAD'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    recent_commits = int(result.stdout.strip())
                    metrics.append(MetricRecord(timestamp, 'git', 'recent_commits_30d', recent_commits, {}))
                    
            except Exception as e:
                logger.warning(f"Failed to get git metrics: {e}")
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
        
        return metrics
    
    def get_historical_data(self, metric_type: str, days: int = 30) -> pd.DataFrame:
        """過去のメトリクスデータを取得"""
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT timestamp, metric_name, value, details
                FROM metrics
                WHERE metric_type = ? AND timestamp >= ?
                ORDER BY timestamp
            """
            df = pd.read_sql_query(query, conn, params=(metric_type, since_date))
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def create_trend_charts(self):
        """トレンドチャートの生成"""
        plt.style.use('seaborn-v0_8')
        
        # テスト成功率のトレンド
        test_df = self.get_historical_data('test', days=90)
        if not test_df.empty:
            success_rate_df = test_df[test_df['metric_name'] == 'success_rate']
            
            if not success_rate_df.empty:
                plt.figure(figsize=(12, 6))
                plt.plot(success_rate_df['timestamp'], success_rate_df['value'], 
                        marker='o', linewidth=2, markersize=4)
                plt.title('📈 Test Success Rate Trend (90 days)', fontsize=14, fontweight='bold')
                plt.xlabel('Date')
                plt.ylabel('Success Rate (%)')
                plt.grid(True, alpha=0.3)
                plt.ylim(0, 100)
                plt.xticks(rotation=45)
                plt.tight_layout()
                plt.savefig(self.charts_dir / 'test-success-rate-trend.png', dpi=150, bbox_inches='tight')
                plt.close()
        
        # カバレッジトレンド
        coverage_df = self.get_historical_data('coverage', days=90)
        if not coverage_df.empty:
            plt.figure(figsize=(12, 6))
            
            for coverage_type in coverage_df['metric_name'].unique():
                type_df = coverage_df[coverage_df['metric_name'] == coverage_type]
                plt.plot(type_df['timestamp'], type_df['value'], 
                        marker='o', label=coverage_type.replace('_coverage', '').title())
            
            plt.title('📊 Code Coverage Trends (90 days)', fontsize=14, fontweight='bold')
            plt.xlabel('Date')
            plt.ylabel('Coverage (%)')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.ylim(0, 100)
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(self.charts_dir / 'coverage-trends.png', dpi=150, bbox_inches='tight')
            plt.close()
        
        # システムメトリクスのトレンド
        system_df = self.get_historical_data('system', days=90)
        if not system_df.empty:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('🔧 System Metrics Trends (90 days)', fontsize=16, fontweight='bold')
            
            metrics_to_plot = ['lines_of_code', 'source_files', 'test_files']
            
            for i, metric in enumerate(metrics_to_plot):
                if i < 4:  # 最大4つのサブプロット
                    row, col = i // 2, i % 2
                    metric_df = system_df[system_df['metric_name'] == metric]
                    
                    if not metric_df.empty:
                        axes[row, col].plot(metric_df['timestamp'], metric_df['value'], 
                                          marker='o', linewidth=2, markersize=4)
                        axes[row, col].set_title(metric.replace('_', ' ').title())
                        axes[row, col].grid(True, alpha=0.3)
                        axes[row, col].tick_params(axis='x', rotation=45)
            
            # 未使用のサブプロットを非表示
            if len(metrics_to_plot) < 4:
                for i in range(len(metrics_to_plot), 4):
                    row, col = i // 2, i % 2
                    axes[row, col].set_visible(False)
            
            plt.tight_layout()
            plt.savefig(self.charts_dir / 'system-metrics-trends.png', dpi=150, bbox_inches='tight')
            plt.close()
    
    def generate_dashboard_html(self) -> str:
        """HTMLダッシュボードの生成"""
        # 最新のメトリクスを取得
        latest_metrics = {}
        
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT metric_type, metric_name, value, MAX(timestamp) as latest
                FROM metrics
                GROUP BY metric_type, metric_name
                ORDER BY latest DESC
            """
            cursor = conn.execute(query)
            
            for row in cursor.fetchall():
                metric_type, metric_name, value, timestamp = row
                if metric_type not in latest_metrics:
                    latest_metrics[metric_type] = {}
                latest_metrics[metric_type][metric_name] = {
                    'value': value,
                    'timestamp': timestamp
                }
        
        # HTMLテンプレート
        html_template = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 News Delivery System - Metrics Dashboard</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f7fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .metric-card {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .metric-card h3 {{ margin-top: 0; color: #2c3e50; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #3498db; }}
        .metric-label {{ color: #7f8c8d; font-size: 0.9em; }}
        .charts-section {{ margin-top: 40px; }}
        .chart-container {{ text-align: center; margin: 20px 0; }}
        .chart-container img {{ max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .updated {{ text-align: center; color: #7f8c8d; font-size: 0.9em; margin-top: 20px; }}
        .status-ok {{ color: #27ae60; }}
        .status-warning {{ color: #f39c12; }}
        .status-error {{ color: #e74c3c; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 News Delivery System - Metrics Dashboard</h1>
            <p>リアルタイムシステム状況とパフォーマンス監視</p>
        </div>
        
        <div class="metric-grid">
            <!-- Test Metrics -->
            <div class="metric-card">
                <h3>🧪 テストメトリクス</h3>
                <div class="metric-value status-ok">{test_success_rate}%</div>
                <div class="metric-label">成功率</div>
                <p>総テスト数: {total_tests} | 通過: {passed_tests} | 失敗: {failed_tests}</p>
            </div>
            
            <!-- Coverage Metrics -->
            <div class="metric-card">
                <h3>📈 カバレッジ</h3>
                <div class="metric-value status-ok">{line_coverage}%</div>
                <div class="metric-label">ライン カバレッジ</div>
                <p>ブランチ: {branch_coverage}% | 関数: {function_coverage}%</p>
            </div>
            
            <!-- System Metrics -->
            <div class="metric-card">
                <h3>🔧 システム統計</h3>
                <div class="metric-value">{lines_of_code}</div>
                <div class="metric-label">コード行数</div>
                <p>ソースファイル: {source_files} | テストファイル: {test_files}</p>
            </div>
            
            <!-- Git Activity -->
            <div class="metric-card">
                <h3>📝 Git アクティビティ</h3>
                <div class="metric-value">{recent_commits}</div>
                <div class="metric-label">過去30日のコミット</div>
                <p>総コミット数: {total_commits}</p>
            </div>
        </div>
        
        <div class="charts-section">
            <h2>📊 トレンドチャート</h2>
            
            <div class="chart-container">
                <h3>テスト成功率の推移</h3>
                <img src="charts/test-success-rate-trend.png" alt="Test Success Rate Trend">
            </div>
            
            <div class="chart-container">
                <h3>コードカバレッジの推移</h3>
                <img src="charts/coverage-trends.png" alt="Coverage Trends">
            </div>
            
            <div class="chart-container">
                <h3>システムメトリクスの推移</h3>
                <img src="charts/system-metrics-trends.png" alt="System Metrics Trends">
            </div>
        </div>
        
        <div class="updated">
            最終更新: {last_updated}
        </div>
    </div>
</body>
</html>
        """
        
        # メトリクス値を取得（デフォルト値付き）
        test_metrics = latest_metrics.get('test', {})
        coverage_metrics = latest_metrics.get('coverage', {})
        system_metrics = latest_metrics.get('system', {})
        git_metrics = latest_metrics.get('git', {})
        
        # HTMLを生成
        html_content = html_template.format(
            test_success_rate=test_metrics.get('success_rate', {}).get('value', 0),
            total_tests=int(test_metrics.get('total_tests', {}).get('value', 0)),
            passed_tests=int(test_metrics.get('passed_tests', {}).get('value', 0)),
            failed_tests=int(test_metrics.get('failed_tests', {}).get('value', 0)),
            line_coverage=coverage_metrics.get('line_coverage', {}).get('value', 0),
            branch_coverage=coverage_metrics.get('branch_coverage', {}).get('value', 0),
            function_coverage=coverage_metrics.get('function_coverage', {}).get('value', 0),
            lines_of_code=int(system_metrics.get('lines_of_code', {}).get('value', 0)),
            source_files=int(system_metrics.get('source_files', {}).get('value', 0)),
            test_files=int(system_metrics.get('test_files', {}).get('value', 0)),
            recent_commits=int(git_metrics.get('recent_commits_30d', {}).get('value', 0)),
            total_commits=int(git_metrics.get('total_commits', {}).get('value', 0)),
            last_updated=datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')
        )
        
        return html_content
    
    def update_dashboard(self):
        """ダッシュボード全体の更新"""
        logger.info("Updating metrics dashboard...")
        
        # 最新メトリクスを収集・保存
        all_metrics = []
        all_metrics.extend(self.load_test_metrics())
        all_metrics.extend(self.load_performance_metrics())
        all_metrics.extend(self.load_system_metrics())
        
        for metric in all_metrics:
            self.save_metric(metric)
        
        logger.info(f"Saved {len(all_metrics)} metrics to database")
        
        # チャートを生成
        self.create_trend_charts()
        logger.info("Generated trend charts")
        
        # HTMLダッシュボードを生成
        html_content = self.generate_dashboard_html()
        dashboard_file = self.metrics_dir / "dashboard.html"
        
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Dashboard updated: {dashboard_file}")
        
        # サマリーレポートを生成
        self.generate_summary_report()
        
        return dashboard_file

    def generate_summary_report(self):
        """サマリーレポートの生成"""
        with sqlite3.connect(self.db_path) as conn:
            # 最新のメトリクス概要
            query = """
                SELECT 
                    metric_type,
                    COUNT(*) as metric_count,
                    MAX(timestamp) as latest_update
                FROM metrics
                WHERE timestamp >= date('now', '-7 days')
                GROUP BY metric_type
                ORDER BY latest_update DESC
            """
            
            df = pd.read_sql_query(query, conn)
        
        report = f"""# 📊 Weekly Metrics Summary

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📈 Metrics Overview (Last 7 days)

| Type | Metrics Count | Latest Update |
|------|---------------|---------------|
"""
        
        for _, row in df.iterrows():
            report += f"| {row['metric_type']} | {row['metric_count']} | {row['latest_update']} |\n"
        
        report += f"""

## 📁 Files Generated

- Dashboard: `metrics/dashboard.html`
- Charts: `metrics/charts/*.png`
- Database: `{self.db_path}`

## 🔗 Quick Access

- [View Dashboard](dashboard.html)
- [Test Success Rate](charts/test-success-rate-trend.png)
- [Coverage Trends](charts/coverage-trends.png)
- [System Metrics](charts/system-metrics-trends.png)
"""
        
        with open(self.reports_dir / 'weekly-summary.md', 'w', encoding='utf-8') as f:
            f.write(report)

def main():
    """メイン実行関数"""
    dashboard = MetricsDashboard()
    
    try:
        dashboard_file = dashboard.update_dashboard()
        print(f"✅ Dashboard updated successfully: {dashboard_file}")
        print(f"📊 View dashboard: file://{dashboard_file.absolute()}")
        
    except Exception as e:
        logger.error(f"Failed to update dashboard: {e}")
        raise

if __name__ == "__main__":
    main()