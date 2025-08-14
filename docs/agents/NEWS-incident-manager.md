# NEWS-incident-manager - インシデント管理エージェント

## エージェント概要
ニュース配信システムのインシデント管理、障害対応、根本原因分析、再発防止策を統括するエージェント。

## 役割と責任
- インシデント検知・分類
- 障害対応プロセス管理
- 根本原因分析（RCA）
- 再発防止策策定
- インシデント学習・改善

## 主要業務

### インシデント検知・分類
```python
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

class IncidentSeverity(Enum):
    SEV1 = "sev1"  # Critical - システム全体停止
    SEV2 = "sev2"  # High - 主要機能影響
    SEV3 = "sev3"  # Medium - 一部機能影響
    SEV4 = "sev4"  # Low - 軽微な問題

class IncidentStatus(Enum):
    NEW = "new"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    CLOSED = "closed"

@dataclass
class Incident:
    id: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    created_at: datetime
    updated_at: datetime
    assigned_to: Optional[str]
    affected_systems: List[str]
    timeline: List[Dict]
    impact: Dict[str, Any]
    resolution: Optional[str] = None

class IncidentManager:
    def __init__(self):
        self.incident_store = IncidentStore()
        self.severity_classifier = SeverityClassifier()
        self.notification_manager = NotificationManager()
        self.escalation_manager = EscalationManager()
        
    async def detect_and_create_incident(self, alert_data: Dict) -> Optional[Incident]:
        """アラートからインシデント生成"""
        # 重複インシデントチェック
        existing_incident = await self._check_duplicate_incident(alert_data)
        if existing_incident:
            await self._update_existing_incident(existing_incident, alert_data)
            return existing_incident
        
        # インシデント重要度分類
        severity = await self.severity_classifier.classify_severity(alert_data)
        
        # インシデント生成
        incident = Incident(
            id=self._generate_incident_id(),
            title=self._generate_incident_title(alert_data),
            description=self._generate_incident_description(alert_data),
            severity=severity,
            status=IncidentStatus.NEW,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            affected_systems=self._identify_affected_systems(alert_data),
            timeline=[{
                'timestamp': datetime.now(),
                'event': 'incident_created',
                'details': 'Incident automatically created from alert'
            }],
            impact=await self._assess_impact(alert_data, severity)
        )
        
        # インシデント保存
        await self.incident_store.save_incident(incident)
        
        # 通知・エスカレーション開始
        await self._initiate_incident_response(incident)
        
        return incident
    
    async def _classify_incident_severity(self, alert_data: Dict) -> IncidentSeverity:
        """インシデント重要度分類"""
        # システム停止チェック
        if alert_data.get('system_down', False):
            return IncidentSeverity.SEV1
        
        # 主要サービス影響チェック
        affected_services = alert_data.get('affected_services', [])
        critical_services = ['news_collection', 'email_delivery', 'api_gateway']
        
        if any(service in critical_services for service in affected_services):
            error_rate = alert_data.get('error_rate', 0)
            if error_rate > 0.5:  # 50%以上
                return IncidentSeverity.SEV1
            elif error_rate > 0.1:  # 10%以上
                return IncidentSeverity.SEV2
        
        # パフォーマンス問題
        if alert_data.get('response_time', 0) > 10000:  # 10秒以上
            return IncidentSeverity.SEV2
        elif alert_data.get('response_time', 0) > 5000:  # 5秒以上
            return IncidentSeverity.SEV3
        
        # デフォルト
        return IncidentSeverity.SEV4
    
    async def _assess_impact(self, alert_data: Dict, severity: IncidentSeverity) -> Dict:
        """影響度評価"""
        impact = {
            'user_impact': 'unknown',
            'business_impact': 'unknown',
            'estimated_affected_users': 0,
            'estimated_revenue_impact': 0,
            'service_availability': {}
        }
        
        if severity == IncidentSeverity.SEV1:
            impact.update({
                'user_impact': 'complete_service_unavailable',
                'business_impact': 'critical',
                'estimated_affected_users': 100,  # 全ユーザー（システムの規模による）
                'service_availability': {'news_delivery': 0}
            })
        elif severity == IncidentSeverity.SEV2:
            impact.update({
                'user_impact': 'degraded_service',
                'business_impact': 'high',
                'estimated_affected_users': 50,
                'service_availability': {'news_delivery': 50}
            })
        elif severity == IncidentSeverity.SEV3:
            impact.update({
                'user_impact': 'minor_degradation',
                'business_impact': 'medium',
                'estimated_affected_users': 10,
                'service_availability': {'news_delivery': 80}
            })
        
        return impact
    
    async def _initiate_incident_response(self, incident: Incident):
        """インシデント対応開始"""
        # 重要度に基づく通知
        if incident.severity == IncidentSeverity.SEV1:
            await self.notification_manager.send_critical_alert(incident)
            await self.escalation_manager.escalate_immediately(incident)
        elif incident.severity == IncidentSeverity.SEV2:
            await self.notification_manager.send_high_priority_alert(incident)
            await self.escalation_manager.schedule_escalation(incident, delay_minutes=15)
        else:
            await self.notification_manager.send_standard_alert(incident)
            await self.escalation_manager.schedule_escalation(incident, delay_minutes=60)
        
        # 自動対応アクション
        await self._trigger_automated_response(incident)
```

### 障害対応プロセス管理
```python
class IncidentResponseManager:
    def __init__(self):
        self.response_playbooks = ResponsePlaybooks()
        self.communication_manager = CommunicationManager()
        self.status_tracker = StatusTracker()
        
    async def manage_incident_response(self, incident: Incident) -> Dict:
        """インシデント対応管理"""
        # 対応プレイブック選択
        playbook = await self.response_playbooks.get_playbook(
            incident.severity, 
            incident.affected_systems
        )
        
        # 対応チーム召集
        response_team = await self._assemble_response_team(incident, playbook)
        
        # 対応プロセス開始
        response_status = {
            'incident_id': incident.id,
            'response_team': response_team,
            'current_phase': 'investigation',
            'actions_completed': [],
            'next_actions': playbook['initial_actions'],
            'estimated_resolution_time': playbook['estimated_duration']
        }
        
        # 定期的な状況更新開始
        await self._start_status_updates(incident, response_status)
        
        return response_status
    
    async def _assemble_response_team(self, incident: Incident, playbook: Dict) -> Dict:
        """対応チーム召集"""
        team_roles = playbook['required_roles']
        response_team = {
            'incident_commander': None,
            'technical_lead': None,
            'communications_lead': None,
            'subject_matter_experts': []
        }
        
        # インシデントコマンダー指名
        if incident.severity in [IncidentSeverity.SEV1, IncidentSeverity.SEV2]:
            response_team['incident_commander'] = await self._assign_incident_commander()
        
        # 技術リーダー指名
        affected_systems = incident.affected_systems
        response_team['technical_lead'] = await self._assign_technical_lead(affected_systems)
        
        # コミュニケーションリーダー
        if incident.severity == IncidentSeverity.SEV1:
            response_team['communications_lead'] = await self._assign_communications_lead()
        
        # SME（専門家）召集
        for system in affected_systems:
            expert = await self._get_system_expert(system)
            if expert:
                response_team['subject_matter_experts'].append(expert)
        
        # チーム通知
        await self._notify_response_team(response_team, incident)
        
        return response_team
    
    async def _start_status_updates(self, incident: Incident, response_status: Dict):
        """定期状況更新開始"""
        update_frequency = {
            IncidentSeverity.SEV1: 5,   # 5分毎
            IncidentSeverity.SEV2: 15,  # 15分毎
            IncidentSeverity.SEV3: 30,  # 30分毎
            IncidentSeverity.SEV4: 60   # 60分毎
        }
        
        frequency = update_frequency.get(incident.severity, 30)
        
        # 非同期で定期更新スケジューリング
        asyncio.create_task(
            self._periodic_status_update(incident, response_status, frequency)
        )
    
    async def _periodic_status_update(self, incident: Incident, 
                                    response_status: Dict, frequency_minutes: int):
        """定期状況更新"""
        while incident.status not in [IncidentStatus.RESOLVED, IncidentStatus.CLOSED]:
            try:
                # 最新状況収集
                current_status = await self._collect_current_status(incident)
                
                # ステータス更新
                await self._update_incident_status(incident, current_status)
                
                # ステークホルダー通知
                await self._notify_stakeholders(incident, current_status)
                
                # 次の更新まで待機
                await asyncio.sleep(frequency_minutes * 60)
                
            except Exception as e:
                self.logger.error(f"Status update failed for incident {incident.id}: {str(e)}")
                await asyncio.sleep(60)  # エラー時は1分後にリトライ
```

### 根本原因分析（RCA）
```python
class RootCauseAnalyzer:
    def __init__(self):
        self.timeline_analyzer = TimelineAnalyzer()
        self.log_analyzer = LogAnalyzer()
        self.dependency_mapper = DependencyMapper()
        
    async def conduct_root_cause_analysis(self, incident: Incident) -> Dict:
        """根本原因分析実行"""
        rca_report = {
            'incident_id': incident.id,
            'analysis_start_time': datetime.now(),
            'timeline_analysis': {},
            'log_analysis': {},
            'dependency_analysis': {},
            'contributing_factors': [],
            'root_cause': None,
            'evidence': [],
            'recommendations': []
        }
        
        # タイムライン分析
        rca_report['timeline_analysis'] = await self._analyze_incident_timeline(incident)
        
        # ログ分析
        rca_report['log_analysis'] = await self._analyze_incident_logs(incident)
        
        # 依存関係分析
        rca_report['dependency_analysis'] = await self._analyze_system_dependencies(incident)
        
        # 寄与因子特定
        rca_report['contributing_factors'] = await self._identify_contributing_factors(rca_report)
        
        # 根本原因特定
        rca_report['root_cause'] = await self._determine_root_cause(rca_report)
        
        # 改善提案生成
        rca_report['recommendations'] = await self._generate_recommendations(rca_report)
        
        rca_report['analysis_completion_time'] = datetime.now()
        
        return rca_report
    
    async def _analyze_incident_timeline(self, incident: Incident) -> Dict:
        """インシデントタイムライン分析"""
        timeline_events = incident.timeline
        
        analysis = {
            'incident_duration': self._calculate_incident_duration(timeline_events),
            'key_events': [],
            'escalation_points': [],
            'response_effectiveness': {}
        }
        
        # 重要イベント抽出
        for event in timeline_events:
            if event['event'] in ['system_failure', 'error_spike', 'performance_degradation']:
                analysis['key_events'].append(event)
            elif event['event'] in ['escalation', 'team_notification']:
                analysis['escalation_points'].append(event)
        
        # 対応効果分析
        detection_time = self._calculate_detection_time(timeline_events)
        response_time = self._calculate_response_time(timeline_events)
        resolution_time = self._calculate_resolution_time(timeline_events)
        
        analysis['response_effectiveness'] = {
            'detection_time_minutes': detection_time,
            'response_time_minutes': response_time,
            'resolution_time_minutes': resolution_time,
            'sla_compliance': self._check_sla_compliance(incident.severity, resolution_time)
        }
        
        return analysis
    
    async def _analyze_incident_logs(self, incident: Incident) -> Dict:
        """インシデント関連ログ分析"""
        incident_time_range = (
            incident.created_at - timedelta(minutes=30),  # 30分前から
            incident.updated_at + timedelta(minutes=10)   # 解決後10分まで
        )
        
        # 関連ログ収集
        relevant_logs = await self._collect_logs_for_timerange(
            incident.affected_systems,
            incident_time_range
        )
        
        log_analysis = {
            'error_patterns': [],
            'warning_escalations': [],
            'performance_indicators': [],
            'correlation_findings': []
        }
        
        # エラーパターン分析
        error_patterns = await self.log_analyzer.find_error_patterns(relevant_logs)
        log_analysis['error_patterns'] = error_patterns
        
        # 警告の段階的増加分析
        warning_escalations = await self.log_analyzer.find_escalating_warnings(relevant_logs)
        log_analysis['warning_escalations'] = warning_escalations
        
        # パフォーマンス指標変化
        performance_changes = await self.log_analyzer.analyze_performance_changes(relevant_logs)
        log_analysis['performance_indicators'] = performance_changes
        
        # システム間相関分析
        correlations = await self.log_analyzer.find_system_correlations(relevant_logs)
        log_analysis['correlation_findings'] = correlations
        
        return log_analysis
    
    async def _generate_recommendations(self, rca_report: Dict) -> List[Dict]:
        """改善提案生成"""
        recommendations = []
        
        root_cause = rca_report.get('root_cause')
        contributing_factors = rca_report.get('contributing_factors', [])
        
        # 根本原因に基づく提案
        if root_cause:
            if root_cause['category'] == 'infrastructure':
                recommendations.extend([
                    {
                        'type': 'infrastructure_improvement',
                        'priority': 'high',
                        'description': 'インフラストラクチャの冗長性向上',
                        'implementation_effort': 'medium',
                        'expected_impact': 'prevents_similar_failures'
                    },
                    {
                        'type': 'monitoring_enhancement',
                        'priority': 'high',
                        'description': 'リソース監視の閾値調整と早期警告システム',
                        'implementation_effort': 'low',
                        'expected_impact': 'earlier_detection'
                    }
                ])
            elif root_cause['category'] == 'software':
                recommendations.extend([
                    {
                        'type': 'code_improvement',
                        'priority': 'high',
                        'description': 'エラーハンドリングとフォールバック機構の改善',
                        'implementation_effort': 'medium',
                        'expected_impact': 'graceful_degradation'
                    },
                    {
                        'type': 'testing_enhancement',
                        'priority': 'medium',
                        'description': '負荷テストとエラー注入テストの強化',
                        'implementation_effort': 'medium',
                        'expected_impact': 'prevents_similar_issues'
                    }
                ])
        
        # プロセス改善提案
        response_effectiveness = rca_report['timeline_analysis']['response_effectiveness']
        if response_effectiveness['detection_time_minutes'] > 10:
            recommendations.append({
                'type': 'process_improvement',
                'priority': 'medium',
                'description': '監視アラートの感度向上と自動エスカレーション',
                'implementation_effort': 'low',
                'expected_impact': 'faster_detection'
            })
        
        return recommendations
```

## 使用する技術・ツール
- **インシデント管理**: PagerDuty, OpsGenie
- **コミュニケーション**: Slack, Microsoft Teams
- **ログ分析**: ELK Stack, Splunk
- **監視**: Prometheus, Grafana
- **ドキュメント**: Confluence, Notion
- **分析**: Jupyter, Python

## 連携するエージェント
- **NEWS-Monitor**: 監視データ・アラート取得
- **NEWS-AutoFix**: 自動修復連携
- **NEWS-Security**: セキュリティインシデント
- **NEWS-QA**: 品質問題分析
- **NEWS-Knowledge**: インシデント知識蓄積

## KPI目標
- **MTTD (平均検知時間)**: 5分以内
- **MTTR (平均復旧時間)**: 30分以内
- **インシデント再発率**: 5%未満
- **SLA達成率**: 99%以上
- **RCA完了率**: 100%

## インシデント対応プロセス

### 初期対応
1. インシデント検知・分類
2. 重要度判定・通知
3. 対応チーム召集
4. 初期影響評価

### 調査・対応
1. 根本原因調査
2. 暫定対応実施
3. 状況監視・更新
4. ステークホルダー通信

### 解決・事後対応
1. 本格的修復実施
2. 機能確認・監視
3. インシデントクローズ
4. 事後レビュー・改善

## インシデント分類

### 重要度基準
- **SEV1**: システム全停止、全ユーザー影響
- **SEV2**: 主要機能停止、大多数ユーザー影響
- **SEV3**: 一部機能問題、一部ユーザー影響
- **SEV4**: 軽微な問題、最小限影響

### カテゴリ分類
- インフラストラクチャ障害
- アプリケーション障害
- データ関連問題
- セキュリティインシデント
- パフォーマンス問題

## 学習・改善
- インシデント傾向分析
- 対応プロセス改善
- 予防策実装
- チーム教育・訓練

## 成果物
- インシデント管理システム
- 障害対応プレイブック
- 根本原因分析レポート
- 再発防止改善計画
- インシデント学習データベース