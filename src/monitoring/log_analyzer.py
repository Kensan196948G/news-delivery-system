"""
高度なログ分析エンジン
ログパターン分析、エラートレンド検出、パフォーマンス異常検知を実装
"""
import asyncio
import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Pattern
from dataclasses import dataclass, field
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import logging
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import IsolationForest
import numpy as np
import pandas as pd
from scipy import stats
import threading
import time
from queue import Queue, Empty
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class LogEntry:
    """ログエントリを表現するデータクラス"""
    timestamp: datetime
    level: str
    module: str
    message: str
    raw_line: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level,
            'module': self.module,
            'message': self.message,
            'raw_line': self.raw_line,
            'metadata': self.metadata
        }

@dataclass
class LogPattern:
    """検出されたログパターン"""
    pattern_id: str
    regex_pattern: str
    frequency: int
    first_seen: datetime
    last_seen: datetime
    severity: str
    description: str
    examples: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'pattern_id': self.pattern_id,
            'regex_pattern': self.regex_pattern,
            'frequency': self.frequency,
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'severity': self.severity,
            'description': self.description,
            'examples': self.examples[:5]  # 最大5個の例を保持
        }

@dataclass
class AnomalyDetection:
    """異常検知結果"""
    timestamp: datetime
    anomaly_type: str
    severity: float
    description: str
    affected_metrics: List[str]
    confidence_score: float
    details: Dict[str, Any] = field(default_factory=dict)

class LogPatternDetector:
    """ログパターン検出エンジン"""
    
    def __init__(self):
        self.patterns: Dict[str, LogPattern] = {}
        self.compiled_patterns: Dict[str, Pattern] = {}
        self.min_frequency = 3
        self.pattern_cache = {}
        
        # 事前定義された重要パターン
        self.predefined_patterns = {
            'error_404': r'HTTP/\d\.\d"\s+404',
            'error_500': r'HTTP/\d\.\d"\s+5\d\d',
            'connection_timeout': r'(timeout|timed out|connection.*timeout)',
            'memory_error': r'(OutOfMemoryError|MemoryError|out of memory)',
            'database_error': r'(DatabaseError|SQL.*Error|connection.*database)',
            'authentication_error': r'(authentication.*failed|unauthorized|invalid.*credentials)',
            'api_rate_limit': r'(rate.*limit|too many requests|quota.*exceeded)',
            'disk_space': r'(disk.*full|no space left|filesystem.*full)',
            'network_error': r'(network.*unreachable|connection.*refused|host.*unreachable)',
            'ssl_error': r'(SSL.*error|certificate.*error|TLS.*handshake)'
        }
        
        # パターンをコンパイル
        for pattern_id, pattern in self.predefined_patterns.items():
            self.compiled_patterns[pattern_id] = re.compile(pattern, re.IGNORECASE)
    
    def detect_patterns(self, log_entries: List[LogEntry]) -> List[LogPattern]:
        """ログエントリからパターンを検出"""
        pattern_matches = defaultdict(list)
        
        # 事前定義パターンのマッチング
        for entry in log_entries:
            for pattern_id, compiled_pattern in self.compiled_patterns.items():
                if compiled_pattern.search(entry.message) or compiled_pattern.search(entry.raw_line):
                    pattern_matches[pattern_id].append(entry)
        
        # 動的パターン検出
        dynamic_patterns = self._detect_dynamic_patterns(log_entries)
        pattern_matches.update(dynamic_patterns)
        
        # LogPatternオブジェクトに変換
        detected_patterns = []
        for pattern_id, matches in pattern_matches.items():
            if len(matches) >= self.min_frequency:
                pattern = LogPattern(
                    pattern_id=pattern_id,
                    regex_pattern=self.predefined_patterns.get(pattern_id, "dynamic"),
                    frequency=len(matches),
                    first_seen=min(match.timestamp for match in matches),
                    last_seen=max(match.timestamp for match in matches),
                    severity=self._calculate_severity(pattern_id, matches),
                    description=self._generate_description(pattern_id, matches),
                    examples=[match.message for match in matches[:5]]
                )
                detected_patterns.append(pattern)
                self.patterns[pattern_id] = pattern
        
        return detected_patterns
    
    def _detect_dynamic_patterns(self, log_entries: List[LogEntry]) -> Dict[str, List[LogEntry]]:
        """機械学習による動的パターン検出"""
        if len(log_entries) < 10:
            return {}
        
        # エラーレベルのログのみを対象
        error_logs = [entry for entry in log_entries if entry.level in ['ERROR', 'CRITICAL']]
        
        if len(error_logs) < 5:
            return {}
        
        # TF-IDFベクトル化
        messages = [entry.message for entry in error_logs]
        vectorizer = TfidfVectorizer(max_features=100, stop_words='english', ngram_range=(1, 2))
        
        try:
            tfidf_matrix = vectorizer.fit_transform(messages)
            
            # DBSCANクラスタリングでパターンをグループ化
            clustering = DBSCAN(eps=0.5, min_samples=3)
            cluster_labels = clustering.fit_predict(tfidf_matrix.toarray())
            
            # クラスタごとにパターンを作成
            dynamic_patterns = defaultdict(list)
            for i, label in enumerate(cluster_labels):
                if label != -1:  # ノイズではない
                    cluster_id = f"dynamic_cluster_{label}"
                    dynamic_patterns[cluster_id].append(error_logs[i])
            
            return dict(dynamic_patterns)
        
        except Exception as e:
            logger.warning(f"Dynamic pattern detection failed: {e}")
            return {}
    
    def _calculate_severity(self, pattern_id: str, matches: List[LogEntry]) -> str:
        """パターンの重要度を計算"""
        error_count = sum(1 for match in matches if match.level in ['ERROR', 'CRITICAL'])
        error_ratio = error_count / len(matches)
        
        if error_ratio > 0.8 or pattern_id in ['memory_error', 'disk_space', 'database_error']:
            return 'CRITICAL'
        elif error_ratio > 0.5 or pattern_id in ['connection_timeout', 'api_rate_limit']:
            return 'HIGH'
        elif error_ratio > 0.2 or pattern_id in ['error_404', 'authentication_error']:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _generate_description(self, pattern_id: str, matches: List[LogEntry]) -> str:
        """パターンの説明を生成"""
        descriptions = {
            'error_404': 'HTTPリソースが見つからない',
            'error_500': 'サーバー内部エラー',
            'connection_timeout': '接続タイムアウトが発生',
            'memory_error': 'メモリ不足エラー',
            'database_error': 'データベース接続エラー',
            'authentication_error': '認証失敗',
            'api_rate_limit': 'API呼び出し制限に達した',
            'disk_space': 'ディスク容量不足',
            'network_error': 'ネットワーク接続エラー',
            'ssl_error': 'SSL/TLS証明書エラー'
        }
        
        if pattern_id in descriptions:
            return descriptions[pattern_id]
        elif pattern_id.startswith('dynamic_cluster_'):
            return f'動的検出パターン (クラスタ {pattern_id.split("_")[-1]})'
        else:
            return f'不明なパターン: {pattern_id}'

class PerformanceAnomalyDetector:
    """パフォーマンス異常検知"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.models: Dict[str, IsolationForest] = {}
        self.thresholds: Dict[str, Dict[str, float]] = {}
        
    def add_metric(self, metric_name: str, value: float, timestamp: datetime = None):
        """メトリクス値を追加"""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.metrics_history[metric_name].append({
            'value': value,
            'timestamp': timestamp
        })
        
        # 十分なデータが蓄積されたら閾値を更新
        if len(self.metrics_history[metric_name]) >= 20:
            self._update_thresholds(metric_name)
    
    def detect_anomalies(self, current_metrics: Dict[str, float]) -> List[AnomalyDetection]:
        """現在のメトリクスから異常を検出"""
        anomalies = []
        current_time = datetime.now()
        
        for metric_name, value in current_metrics.items():
            # 統計的異常検出
            statistical_anomaly = self._detect_statistical_anomaly(metric_name, value, current_time)
            if statistical_anomaly:
                anomalies.append(statistical_anomaly)
            
            # 機械学習による異常検出
            ml_anomaly = self._detect_ml_anomaly(metric_name, value, current_time)
            if ml_anomaly:
                anomalies.append(ml_anomaly)
            
            # メトリクス値を履歴に追加
            self.add_metric(metric_name, value, current_time)
        
        return anomalies
    
    def _detect_statistical_anomaly(
        self, 
        metric_name: str, 
        value: float, 
        timestamp: datetime
    ) -> Optional[AnomalyDetection]:
        """統計的手法による異常検出"""
        if metric_name not in self.metrics_history or len(self.metrics_history[metric_name]) < 10:
            return None
        
        history = [item['value'] for item in self.metrics_history[metric_name]]
        mean = np.mean(history)
        std = np.std(history)
        
        if std == 0:
            return None
        
        # Z-scoreで異常検出
        z_score = abs(value - mean) / std
        
        if z_score > 3:  # 3シグマルール
            severity = min(z_score / 3, 1.0)  # 0-1の範囲に正規化
            
            return AnomalyDetection(
                timestamp=timestamp,
                anomaly_type='statistical',
                severity=severity,
                description=f'{metric_name}の値が統計的に異常 (Z-score: {z_score:.2f})',
                affected_metrics=[metric_name],
                confidence_score=min(z_score / 5, 1.0),
                details={
                    'z_score': z_score,
                    'mean': mean,
                    'std': std,
                    'current_value': value
                }
            )
        
        return None
    
    def _detect_ml_anomaly(
        self, 
        metric_name: str, 
        value: float, 
        timestamp: datetime
    ) -> Optional[AnomalyDetection]:
        """機械学習による異常検出"""
        if metric_name not in self.metrics_history or len(self.metrics_history[metric_name]) < 30:
            return None
        
        # モデルが存在しない場合は作成
        if metric_name not in self.models:
            self._train_model(metric_name)
        
        model = self.models[metric_name]
        
        # 異常スコアを計算
        anomaly_score = model.decision_function([[value]])[0]
        is_anomaly = model.predict([[value]])[0] == -1
        
        if is_anomaly:
            # 異常スコアを0-1の範囲に正規化
            severity = max(0, min(1, (-anomaly_score + 0.5) / 0.5))
            
            return AnomalyDetection(
                timestamp=timestamp,
                anomaly_type='machine_learning',
                severity=severity,
                description=f'{metric_name}の値がML異常検知により検出',
                affected_metrics=[metric_name],
                confidence_score=severity,
                details={
                    'anomaly_score': anomaly_score,
                    'current_value': value,
                    'model_type': 'IsolationForest'
                }
            )
        
        return None
    
    def _train_model(self, metric_name: str):
        """指定メトリクスのML異常検知モデルを訓練"""
        if len(self.metrics_history[metric_name]) < 30:
            return
        
        history_values = [[item['value']] for item in self.metrics_history[metric_name]]
        
        model = IsolationForest(
            contamination=0.1,  # 10%を異常とする
            random_state=42
        )
        model.fit(history_values)
        
        self.models[metric_name] = model
    
    def _update_thresholds(self, metric_name: str):
        """統計的閾値を更新"""
        history = [item['value'] for item in self.metrics_history[metric_name]]
        
        self.thresholds[metric_name] = {
            'mean': np.mean(history),
            'std': np.std(history),
            'p95': np.percentile(history, 95),
            'p99': np.percentile(history, 99),
            'min': np.min(history),
            'max': np.max(history)
        }

class LogAnalysisEngine:
    """メインログ分析エンジン"""
    
    def __init__(self, log_directory: str, db_path: str = None):
        self.log_directory = Path(log_directory)
        self.db_path = db_path or "logs_analysis.db"
        self.pattern_detector = LogPatternDetector()
        self.anomaly_detector = PerformanceAnomalyDetector()
        
        # ログパーサーの正規表現パターン
        self.log_patterns = {
            'python_logging': re.compile(
                r'\[(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\]\s+'
                r'\[(?P<level>\w+)\]\s+\[(?P<module>[\w\.]+)\]\s+(?P<message>.*)'
            ),
            'standard': re.compile(
                r'(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
                r'(?P<level>\w+)\s+(?P<module>\S+)\s+(?P<message>.*)'
            )
        }
        
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._init_database()
    
    def _init_database(self):
        """分析結果保存用データベースを初期化"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS log_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    regex_pattern TEXT,
                    frequency INTEGER,
                    first_seen TEXT,
                    last_seen TEXT,
                    severity TEXT,
                    description TEXT,
                    examples TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS anomalies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    anomaly_type TEXT,
                    severity REAL,
                    description TEXT,
                    affected_metrics TEXT,
                    confidence_score REAL,
                    details TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_summary (
                    analysis_time TEXT,
                    log_files_processed INTEGER,
                    total_entries INTEGER,
                    error_entries INTEGER,
                    patterns_detected INTEGER,
                    anomalies_detected INTEGER
                )
            """)
    
    async def analyze_logs(
        self, 
        time_range: Optional[Tuple[datetime, datetime]] = None,
        log_levels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """ログファイルを分析してパターンと異常を検出"""
        logger.info("Starting comprehensive log analysis")
        
        # ログファイルを収集
        log_files = self._collect_log_files(time_range)
        logger.info(f"Found {len(log_files)} log files to analyze")
        
        # ログエントリをパース
        log_entries = []
        for log_file in log_files:
            entries = await self._parse_log_file(log_file, log_levels)
            log_entries.extend(entries)
        
        logger.info(f"Parsed {len(log_entries)} log entries")
        
        if not log_entries:
            return {
                'summary': {
                    'log_files_processed': len(log_files),
                    'total_entries': 0,
                    'patterns_detected': 0,
                    'anomalies_detected': 0
                },
                'patterns': [],
                'anomalies': [],
                'metrics': {}
            }
        
        # パターン検出を並行実行
        patterns_task = asyncio.create_task(
            self._run_pattern_detection(log_entries)
        )
        
        # メトリクス分析を並行実行
        metrics_task = asyncio.create_task(
            self._analyze_metrics(log_entries)
        )
        
        # 結果を待つ
        detected_patterns = await patterns_task
        metrics_analysis = await metrics_task
        
        # 異常検知
        anomalies = []
        if metrics_analysis['performance_metrics']:
            anomalies = self.anomaly_detector.detect_anomalies(
                metrics_analysis['performance_metrics']
            )
        
        # 結果をデータベースに保存
        await self._save_analysis_results(detected_patterns, anomalies)
        
        # サマリーを作成
        summary = {
            'analysis_time': datetime.now().isoformat(),
            'log_files_processed': len(log_files),
            'total_entries': len(log_entries),
            'error_entries': sum(1 for entry in log_entries if entry.level in ['ERROR', 'CRITICAL']),
            'patterns_detected': len(detected_patterns),
            'anomalies_detected': len(anomalies)
        }
        
        logger.info(f"Analysis complete: {summary}")
        
        return {
            'summary': summary,
            'patterns': [pattern.to_dict() for pattern in detected_patterns],
            'anomalies': [anomaly.__dict__ for anomaly in anomalies],
            'metrics': metrics_analysis,
            'trends': self._calculate_trends(log_entries),
            'recommendations': self._generate_recommendations(detected_patterns, anomalies)
        }
    
    def _collect_log_files(self, time_range: Optional[Tuple[datetime, datetime]] = None) -> List[Path]:
        """指定時間範囲のログファイルを収集"""
        log_files = []
        
        if not self.log_directory.exists():
            logger.warning(f"Log directory not found: {self.log_directory}")
            return log_files
        
        for log_file in self.log_directory.rglob("*.log"):
            if time_range:
                # ファイルの最終更新時刻をチェック
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if not (time_range[0] <= file_mtime <= time_range[1]):
                    continue
            
            log_files.append(log_file)
        
        return sorted(log_files, key=lambda f: f.stat().st_mtime)
    
    async def _parse_log_file(
        self, 
        log_file: Path, 
        log_levels: Optional[List[str]] = None
    ) -> List[LogEntry]:
        """ログファイルをパースしてLogEntryのリストを生成"""
        entries = []
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # ログパターンにマッチを試行
                    parsed_entry = None
                    for pattern_name, pattern in self.log_patterns.items():
                        match = pattern.match(line)
                        if match:
                            parsed_entry = self._create_log_entry(match, line, log_file, line_num)
                            break
                    
                    # パターンにマッチしない場合は簡単なエントリを作成
                    if not parsed_entry:
                        parsed_entry = LogEntry(
                            timestamp=datetime.now(),
                            level='INFO',
                            module=log_file.stem,
                            message=line,
                            raw_line=line,
                            metadata={'file': str(log_file), 'line_number': line_num}
                        )
                    
                    # レベルフィルタリング
                    if log_levels is None or parsed_entry.level in log_levels:
                        entries.append(parsed_entry)
        
        except Exception as e:
            logger.error(f"Error parsing log file {log_file}: {e}")
        
        return entries
    
    def _create_log_entry(self, match: re.Match, raw_line: str, log_file: Path, line_num: int) -> LogEntry:
        """正規表現マッチからLogEntryを作成"""
        groups = match.groupdict()
        
        # タイムスタンプの解析
        timestamp_str = groups.get('timestamp', '')
        try:
            if ',' in timestamp_str:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
            else:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            timestamp = datetime.now()
        
        return LogEntry(
            timestamp=timestamp,
            level=groups.get('level', 'INFO').upper(),
            module=groups.get('module', log_file.stem),
            message=groups.get('message', ''),
            raw_line=raw_line,
            metadata={
                'file': str(log_file),
                'line_number': line_num
            }
        )
    
    async def _run_pattern_detection(self, log_entries: List[LogEntry]) -> List[LogPattern]:
        """パターン検出を別スレッドで実行"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.pattern_detector.detect_patterns,
            log_entries
        )
    
    async def _analyze_metrics(self, log_entries: List[LogEntry]) -> Dict[str, Any]:
        """ログエントリからメトリクスを分析"""
        metrics = {
            'log_level_distribution': defaultdict(int),
            'module_distribution': defaultdict(int),
            'hourly_distribution': defaultdict(int),
            'error_rate_trend': [],
            'performance_metrics': {},
            'top_error_modules': [],
            'response_times': []
        }
        
        # 基本統計の計算
        for entry in log_entries:
            metrics['log_level_distribution'][entry.level] += 1
            metrics['module_distribution'][entry.module] += 1
            metrics['hourly_distribution'][entry.timestamp.hour] += 1
            
            # レスポンス時間の抽出（ログメッセージから）
            response_time = self._extract_response_time(entry.message)
            if response_time:
                metrics['response_times'].append(response_time)
        
        # エラー率のトレンド計算
        metrics['error_rate_trend'] = self._calculate_error_rate_trend(log_entries)
        
        # 上位エラーモジュール
        error_counts = defaultdict(int)
        for entry in log_entries:
            if entry.level in ['ERROR', 'CRITICAL']:
                error_counts[entry.module] += 1
        
        metrics['top_error_modules'] = sorted(
            error_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        # パフォーマンスメトリクス
        if metrics['response_times']:
            metrics['performance_metrics'] = {
                'avg_response_time': np.mean(metrics['response_times']),
                'p95_response_time': np.percentile(metrics['response_times'], 95),
                'p99_response_time': np.percentile(metrics['response_times'], 99),
                'max_response_time': np.max(metrics['response_times']),
                'total_requests': len(metrics['response_times'])
            }
        
        return dict(metrics)
    
    def _extract_response_time(self, message: str) -> Optional[float]:
        """ログメッセージからレスポンス時間を抽出"""
        patterns = [
            r'response time[:\s]*(\d+(?:\.\d+)?)\s*ms',
            r'took[:\s]*(\d+(?:\.\d+)?)\s*ms',
            r'duration[:\s]*(\d+(?:\.\d+)?)\s*ms',
            r'(\d+(?:\.\d+)?)\s*ms'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _calculate_error_rate_trend(self, log_entries: List[LogEntry]) -> List[Dict[str, Any]]:
        """エラー率のトレンドを計算"""
        if not log_entries:
            return []
        
        # 時間別にログエントリをグループ化
        hourly_counts = defaultdict(lambda: {'total': 0, 'errors': 0})
        
        for entry in log_entries:
            hour_key = entry.timestamp.replace(minute=0, second=0, microsecond=0)
            hourly_counts[hour_key]['total'] += 1
            
            if entry.level in ['ERROR', 'CRITICAL']:
                hourly_counts[hour_key]['errors'] += 1
        
        # エラー率を計算
        trend_data = []
        for hour, counts in sorted(hourly_counts.items()):
            error_rate = counts['errors'] / counts['total'] if counts['total'] > 0 else 0
            trend_data.append({
                'timestamp': hour.isoformat(),
                'error_rate': error_rate,
                'total_logs': counts['total'],
                'error_logs': counts['errors']
            })
        
        return trend_data
    
    def _calculate_trends(self, log_entries: List[LogEntry]) -> Dict[str, Any]:
        """長期トレンドの計算"""
        if len(log_entries) < 2:
            return {}
        
        # 日別統計
        daily_stats = defaultdict(lambda: {'total': 0, 'errors': 0})
        
        for entry in log_entries:
            date_key = entry.timestamp.date()
            daily_stats[date_key]['total'] += 1
            
            if entry.level in ['ERROR', 'CRITICAL']:
                daily_stats[date_key]['errors'] += 1
        
        # トレンド分析
        dates = sorted(daily_stats.keys())
        error_rates = [daily_stats[date]['errors'] / daily_stats[date]['total'] 
                      for date in dates]
        
        if len(error_rates) >= 3:
            # 線形回帰によるトレンド計算
            x = np.arange(len(error_rates))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, error_rates)
            
            trend_direction = 'increasing' if slope > 0.001 else 'decreasing' if slope < -0.001 else 'stable'
            
            return {
                'trend_direction': trend_direction,
                'trend_slope': slope,
                'correlation': r_value,
                'p_value': p_value,
                'average_error_rate': np.mean(error_rates),
                'error_rate_variance': np.var(error_rates)
            }
        
        return {}
    
    def _generate_recommendations(
        self, 
        patterns: List[LogPattern], 
        anomalies: List[AnomalyDetection]
    ) -> List[Dict[str, Any]]:
        """分析結果に基づく推奨アクションを生成"""
        recommendations = []
        
        # パターンベースの推奨
        critical_patterns = [p for p in patterns if p.severity == 'CRITICAL']
        if critical_patterns:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Pattern Analysis',
                'description': f'{len(critical_patterns)}個の重要なエラーパターンが検出されました',
                'action': 'これらのパターンの根本原因を調査し、修正計画を策定してください',
                'affected_patterns': [p.pattern_id for p in critical_patterns]
            })
        
        # 異常検知ベースの推奨
        high_severity_anomalies = [a for a in anomalies if a.severity > 0.7]
        if high_severity_anomalies:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Anomaly Detection',
                'description': f'{len(high_severity_anomalies)}個の高重要度異常が検出されました',
                'action': 'システムリソースとパフォーマンスメトリクスを詳細に調査してください',
                'affected_metrics': list(set([m for a in high_severity_anomalies for m in a.affected_metrics]))
            })
        
        # メモリ関連の推奨
        memory_patterns = [p for p in patterns if 'memory' in p.pattern_id.lower()]
        if memory_patterns:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Resource Management',
                'description': 'メモリ関連のエラーパターンが検出されました',
                'action': 'メモリ使用量の監視を強化し、メモリリークの可能性を調査してください',
                'affected_patterns': [p.pattern_id for p in memory_patterns]
            })
        
        return recommendations
    
    async def _save_analysis_results(
        self, 
        patterns: List[LogPattern], 
        anomalies: List[AnomalyDetection]
    ):
        """分析結果をデータベースに保存"""
        with sqlite3.connect(self.db_path) as conn:
            # パターンを保存
            for pattern in patterns:
                conn.execute("""
                    INSERT OR REPLACE INTO log_patterns VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern.pattern_id,
                    pattern.regex_pattern,
                    pattern.frequency,
                    pattern.first_seen.isoformat(),
                    pattern.last_seen.isoformat(),
                    pattern.severity,
                    pattern.description,
                    json.dumps(pattern.examples)
                ))
            
            # 異常を保存
            for anomaly in anomalies:
                conn.execute("""
                    INSERT INTO anomalies (timestamp, anomaly_type, severity, description, 
                                         affected_metrics, confidence_score, details) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    anomaly.timestamp.isoformat(),
                    anomaly.anomaly_type,
                    anomaly.severity,
                    anomaly.description,
                    json.dumps(anomaly.affected_metrics),
                    anomaly.confidence_score,
                    json.dumps(anomaly.details)
                ))
    
    async def get_historical_analysis(
        self, 
        days: int = 7
    ) -> Dict[str, Any]:
        """過去N日間の分析結果を取得"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            # パターン履歴
            patterns_cursor = conn.execute("""
                SELECT * FROM log_patterns 
                WHERE last_seen >= ? 
                ORDER BY frequency DESC
            """, (start_date.isoformat(),))
            
            patterns = []
            for row in patterns_cursor.fetchall():
                patterns.append({
                    'pattern_id': row[0],
                    'frequency': row[2],
                    'severity': row[5],
                    'description': row[6]
                })
            
            # 異常履歴
            anomalies_cursor = conn.execute("""
                SELECT * FROM anomalies 
                WHERE timestamp >= ? 
                ORDER BY severity DESC, timestamp DESC
            """, (start_date.isoformat(),))
            
            anomalies = []
            for row in anomalies_cursor.fetchall():
                anomalies.append({
                    'timestamp': row[1],
                    'anomaly_type': row[2],
                    'severity': row[3],
                    'description': row[4],
                    'confidence_score': row[6]
                })
        
        return {
            'time_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'patterns': patterns,
            'anomalies': anomalies
        }

# 使用例とテスト用の関数
async def test_log_analysis():
    """ログ分析エンジンのテスト"""
    engine = LogAnalysisEngine("logs")
    
    # 過去24時間のログを分析
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    
    results = await engine.analyze_logs(
        time_range=(start_time, end_time),
        log_levels=['ERROR', 'WARNING', 'INFO']
    )
    
    print("=== ログ分析結果 ===")
    print(f"処理ファイル数: {results['summary']['log_files_processed']}")
    print(f"総エントリ数: {results['summary']['total_entries']}")
    print(f"検出パターン数: {results['summary']['patterns_detected']}")
    print(f"検出異常数: {results['summary']['anomalies_detected']}")
    
    if results['patterns']:
        print("\n=== 検出されたパターン ===")
        for pattern in results['patterns'][:5]:
            print(f"- {pattern['pattern_id']}: {pattern['description']} "
                  f"(頻度: {pattern['frequency']}, 重要度: {pattern['severity']})")
    
    if results['anomalies']:
        print("\n=== 検出された異常 ===")
        for anomaly in results['anomalies'][:5]:
            print(f"- {anomaly['description']} "
                  f"(重要度: {anomaly['severity']:.2f}, 信頼度: {anomaly['confidence_score']:.2f})")
    
    if results['recommendations']:
        print("\n=== 推奨アクション ===")
        for rec in results['recommendations']:
            print(f"- [{rec['priority']}] {rec['description']}")
            print(f"  アクション: {rec['action']}")

if __name__ == "__main__":
    asyncio.run(test_log_analysis())