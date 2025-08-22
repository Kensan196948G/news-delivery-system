#!/usr/bin/env python3
"""
ベンチマーク結果の比較とパフォーマンス劣化検出
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BenchmarkComparator:
    def __init__(self, threshold_percent: float = 20.0):
        """
        Args:
            threshold_percent: パフォーマンス劣化の閾値（％）
        """
        self.threshold = threshold_percent
        
    def load_benchmark_data(self, filepath: str) -> Dict[str, Any]:
        """ベンチマークJSONファイルを読み込み"""
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load benchmark data from {filepath}: {e}")
            return {}
    
    def extract_metrics(self, benchmark_data: Dict[str, Any]) -> Dict[str, float]:
        """ベンチマークデータからメトリクスを抽出"""
        metrics = {}
        
        if 'benchmarks' not in benchmark_data:
            return metrics
            
        for benchmark in benchmark_data['benchmarks']:
            name = benchmark.get('name', 'unknown')
            stats = benchmark.get('stats', {})
            
            # 主要メトリクスを抽出
            if 'mean' in stats:
                metrics[f"{name}_mean"] = stats['mean']
            if 'min' in stats:
                metrics[f"{name}_min"] = stats['min']
            if 'max' in stats:
                metrics[f"{name}_max"] = stats['max']
            if 'stddev' in stats:
                metrics[f"{name}_stddev"] = stats['stddev']
                
        return metrics
    
    def compare_metrics(self, baseline: Dict[str, float], current: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """メトリクスの比較と劣化検出"""
        results = {}
        
        for metric_name in baseline.keys():
            if metric_name not in current:
                continue
                
            baseline_value = baseline[metric_name]
            current_value = current[metric_name]
            
            if baseline_value == 0:
                continue
                
            # パーセンテージ変化を計算
            percent_change = ((current_value - baseline_value) / baseline_value) * 100
            
            # 劣化判定（実行時間の増加は劣化）
            is_regression = percent_change > self.threshold
            
            results[metric_name] = {
                'baseline': baseline_value,
                'current': current_value,
                'percent_change': percent_change,
                'is_regression': is_regression,
                'status': 'REGRESSION' if is_regression else 'OK'
            }
            
        return results
    
    def generate_report(self, comparison_results: Dict[str, Dict[str, Any]]) -> str:
        """比較結果のレポート生成"""
        report_lines = []
        report_lines.append("# 📊 Performance Comparison Report")
        report_lines.append("")
        
        regressions = [k for k, v in comparison_results.items() if v['is_regression']]
        
        if regressions:
            report_lines.append("## ⚠️ Performance Regressions Detected")
            report_lines.append("")
            report_lines.append("| Metric | Baseline | Current | Change | Status |")
            report_lines.append("|--------|----------|---------|--------|--------|")
            
            for metric in regressions:
                data = comparison_results[metric]
                report_lines.append(
                    f"| {metric} | {data['baseline']:.4f} | {data['current']:.4f} | "
                    f"{data['percent_change']:+.2f}% | {data['status']} |"
                )
        else:
            report_lines.append("## ✅ No Performance Regressions")
            
        report_lines.append("")
        report_lines.append("## 📈 All Metrics")
        report_lines.append("")
        report_lines.append("| Metric | Baseline | Current | Change | Status |")
        report_lines.append("|--------|----------|---------|--------|--------|")
        
        for metric, data in comparison_results.items():
            status_emoji = "⚠️" if data['is_regression'] else "✅"
            report_lines.append(
                f"| {metric} | {data['baseline']:.4f} | {data['current']:.4f} | "
                f"{data['percent_change']:+.2f}% | {status_emoji} {data['status']} |"
            )
            
        return "\n".join(report_lines)
    
    def run_comparison(self, baseline_file: str, current_file: str) -> bool:
        """ベンチマーク比較の実行"""
        logger.info(f"Comparing benchmarks: {baseline_file} vs {current_file}")
        
        # データ読み込み
        baseline_data = self.load_benchmark_data(baseline_file)
        current_data = self.load_benchmark_data(current_file)
        
        if not baseline_data or not current_data:
            logger.error("Failed to load benchmark data")
            return False
            
        # メトリクス抽出
        baseline_metrics = self.extract_metrics(baseline_data)
        current_metrics = self.extract_metrics(current_data)
        
        if not baseline_metrics or not current_metrics:
            logger.warning("No metrics found in benchmark data")
            return True
            
        # 比較実行
        comparison_results = self.compare_metrics(baseline_metrics, current_metrics)
        
        # レポート生成
        report = self.generate_report(comparison_results)
        
        # レポートを出力
        print(report)
        
        # ファイルに保存
        with open('performance-comparison-report.md', 'w') as f:
            f.write(report)
            
        # 劣化があったかチェック
        regressions = [k for k, v in comparison_results.items() if v['is_regression']]
        
        if regressions:
            logger.warning(f"Performance regressions detected: {len(regressions)} metrics")
            # GitHub Actionsの場合は環境変数に設定
            with open('performance-regression.txt', 'w') as f:
                f.write(f"REGRESSIONS={len(regressions)}\n")
            return False
        else:
            logger.info("No performance regressions detected")
            return True

def main():
    if len(sys.argv) != 3:
        print("Usage: python compare_benchmarks.py <baseline.json> <current.json>")
        sys.exit(1)
        
    baseline_file = sys.argv[1]
    current_file = sys.argv[2]
    
    comparator = BenchmarkComparator(threshold_percent=20.0)
    success = comparator.run_comparison(baseline_file, current_file)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()