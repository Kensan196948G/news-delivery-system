# NEWS-UX - UX設計エージェント

## エージェント概要
ニュース配信システムのユーザーエクスペリエンス（UX）設計、ユーザビリティ改善を専門とするエージェント。

## 役割と責任
- ユーザーエクスペリエンス設計
- ユーザビリティテスト実行
- インターフェース最適化
- ユーザージャーニー分析
- エンゲージメント向上施策

## 主要業務

### ユーザーエクスペリエンス分析
```python
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class UserJourney:
    user_id: str
    journey_steps: List[Dict]
    total_time: float
    completion_rate: float
    drop_off_points: List[str]
    satisfaction_score: float

class UXAnalyzer:
    def __init__(self):
        self.user_behavior_tracker = UserBehaviorTracker()
        self.engagement_metrics = EngagementMetrics()
        
    async def analyze_user_journey(self, user_interactions: List[Dict]) -> UserJourney:
        """ユーザージャーニー分析"""
        journey_map = self._create_journey_map(user_interactions)
        
        # ユーザージャーニーの各ステップ分析
        journey_steps = []
        total_time = 0
        drop_off_points = []
        
        for step in journey_map:
            step_analysis = await self._analyze_journey_step(step)
            journey_steps.append(step_analysis)
            total_time += step_analysis['duration']
            
            # ドロップオフポイント検出
            if step_analysis['completion_rate'] < 0.7:
                drop_off_points.append(step['step_name'])
        
        completion_rate = self._calculate_completion_rate(journey_steps)
        satisfaction_score = await self._calculate_satisfaction_score(user_interactions)
        
        return UserJourney(
            user_id=user_interactions[0].get('user_id', 'anonymous'),
            journey_steps=journey_steps,
            total_time=total_time,
            completion_rate=completion_rate,
            drop_off_points=drop_off_points,
            satisfaction_score=satisfaction_score
        )
    
    def _create_journey_map(self, interactions: List[Dict]) -> List[Dict]:
        """ジャーニーマップ作成"""
        journey_steps = [
            {'step_name': 'email_open', 'description': 'メール開封'},
            {'step_name': 'content_scan', 'description': 'コンテンツ閲覧'},
            {'step_name': 'category_navigation', 'description': 'カテゴリ移動'},
            {'step_name': 'article_click', 'description': '記事クリック'},
            {'step_name': 'external_link_follow', 'description': '外部リンク遷移'},
            {'step_name': 'engagement_completion', 'description': 'エンゲージメント完了'}
        ]
        
        # インタラクションデータから実際のジャーニーを構築
        actual_journey = []
        for step in journey_steps:
            step_interactions = [
                i for i in interactions 
                if i.get('action_type') == step['step_name']
            ]
            
            if step_interactions:
                actual_journey.append({
                    **step,
                    'interactions': step_interactions,
                    'user_count': len(set(i.get('user_id') for i in step_interactions))
                })
        
        return actual_journey
```

### メールUX最適化
```python
class EmailUXOptimizer:
    def __init__(self):
        self.email_metrics = EmailMetrics()
        self.a_b_tester = ABTester()
        
    async def optimize_email_layout(self, email_performance_data: Dict) -> Dict:
        """メールレイアウト最適化"""
        optimization_recommendations = []
        
        # 開封率分析
        open_rate = email_performance_data.get('open_rate', 0)
        if open_rate < 0.25:  # 25%以下
            optimization_recommendations.append({
                'area': 'subject_line',
                'issue': 'low_open_rate',
                'recommendation': '件名をより魅力的で具体的な内容に変更',
                'expected_improvement': '15-25%'
            })
        
        # クリック率分析
        click_rate = email_performance_data.get('click_through_rate', 0)
        if click_rate < 0.05:  # 5%以下
            optimization_recommendations.append({
                'area': 'content_layout',
                'issue': 'low_engagement',
                'recommendation': 'コンテンツの視覚的階層を改善し、CTA配置を最適化',
                'expected_improvement': '10-20%'
            })
        
        # スクロール深度分析
        scroll_depth = email_performance_data.get('avg_scroll_depth', 0)
        if scroll_depth < 0.6:  # 60%未満
            optimization_recommendations.append({
                'area': 'content_structure',
                'issue': 'poor_content_structure',
                'recommendation': '重要な情報を上部に配置し、要約セクションを追加',
                'expected_improvement': '20-30%'
            })
        
        return {
            'current_performance': email_performance_data,
            'optimization_opportunities': optimization_recommendations,
            'priority_actions': self._prioritize_optimizations(optimization_recommendations)
        }
    
    def design_responsive_email_template(self) -> Dict:
        """レスポンシブメールテンプレート設計"""
        template_design = {
            'mobile_first_approach': True,
            'breakpoints': {
                'mobile': '320px-480px',
                'tablet': '481px-768px', 
                'desktop': '769px+'
            },
            'layout_components': {
                'header': {
                    'mobile': 'single_column_logo',
                    'desktop': 'logo_with_navigation'
                },
                'content_grid': {
                    'mobile': 'single_column',
                    'tablet': 'two_column',
                    'desktop': 'three_column_with_sidebar'
                },
                'typography': {
                    'mobile': {
                        'header_size': '22px',
                        'body_size': '16px',
                        'line_height': '1.6'
                    },
                    'desktop': {
                        'header_size': '28px',
                        'body_size': '14px',
                        'line_height': '1.5'
                    }
                }
            },
            'interaction_design': {
                'touch_targets': '44px_minimum',
                'button_styling': 'rounded_corners_with_clear_labels',
                'link_styling': 'underlined_with_sufficient_contrast'
            }
        }
        
        return template_design
```

### ユーザビリティテスト
```python
class UsabilityTester:
    def __init__(self):
        self.test_scenarios = TestScenarios()
        self.metrics_collector = UsabilityMetrics()
        
    async def conduct_usability_test(self, test_type: str) -> Dict:
        """ユーザビリティテスト実行"""
        if test_type == 'email_navigation':
            return await self._test_email_navigation()
        elif test_type == 'content_findability':
            return await self._test_content_findability()
        elif test_type == 'mobile_experience':
            return await self._test_mobile_experience()
        else:
            return await self._comprehensive_usability_test()
    
    async def _test_email_navigation(self) -> Dict:
        """メール内ナビゲーションテスト"""
        test_tasks = [
            {
                'task': 'find_urgent_news',
                'description': '緊急ニュースを見つける',
                'success_criteria': '30秒以内に緊急セクションを特定'
            },
            {
                'task': 'navigate_to_category',
                'description': '特定カテゴリに移動',
                'success_criteria': 'カテゴリセクションへ直接移動'
            },
            {
                'task': 'access_full_article',
                'description': '完全な記事にアクセス',
                'success_criteria': '外部リンクへの遷移成功'
            }
        ]
        
        test_results = []
        for task in test_tasks:
            task_result = await self._execute_usability_task(task)
            test_results.append(task_result)
        
        overall_score = sum(r['success_rate'] for r in test_results) / len(test_results)
        
        return {
            'test_type': 'email_navigation',
            'overall_usability_score': overall_score,
            'task_results': test_results,
            'recommendations': self._generate_navigation_recommendations(test_results)
        }
    
    async def _test_content_findability(self) -> Dict:
        """コンテンツ発見性テスト"""
        findability_metrics = {
            'time_to_find_relevant_content': await self._measure_content_discovery_time(),
            'content_hierarchy_clarity': await self._assess_information_hierarchy(),
            'search_effectiveness': await self._test_content_search(),
            'category_intuition': await self._test_category_understanding()
        }
        
        findability_score = self._calculate_findability_score(findability_metrics)
        
        return {
            'test_type': 'content_findability',
            'findability_score': findability_score,
            'metrics': findability_metrics,
            'improvement_areas': self._identify_findability_issues(findability_metrics)
        }
```

### エンゲージメント最適化
```python
class EngagementOptimizer:
    def __init__(self):
        self.engagement_analytics = EngagementAnalytics()
        self.personalization_engine = PersonalizationEngine()
        
    async def optimize_user_engagement(self, user_data: Dict) -> Dict:
        """ユーザーエンゲージメント最適化"""
        
        # 現在のエンゲージメントレベル分析
        current_engagement = await self._analyze_current_engagement(user_data)
        
        # パーソナライゼーション機会の特定
        personalization_opportunities = await self._identify_personalization_opportunities(user_data)
        
        # コンテンツ最適化提案
        content_optimizations = await self._suggest_content_optimizations(user_data)
        
        # タイミング最適化
        timing_optimizations = await self._optimize_delivery_timing(user_data)
        
        return {
            'current_engagement_level': current_engagement,
            'optimization_strategies': {
                'personalization': personalization_opportunities,
                'content': content_optimizations,
                'timing': timing_optimizations
            },
            'expected_impact': self._calculate_optimization_impact(
                personalization_opportunities, 
                content_optimizations, 
                timing_optimizations
            )
        }
    
    async def _analyze_current_engagement(self, user_data: Dict) -> Dict:
        """現在のエンゲージメント分析"""
        return {
            'email_open_rate': user_data.get('open_rate', 0),
            'click_through_rate': user_data.get('ctr', 0),
            'time_spent_reading': user_data.get('reading_time', 0),
            'category_preferences': user_data.get('preferred_categories', []),
            'peak_engagement_times': user_data.get('active_hours', []),
            'device_preferences': user_data.get('device_usage', {}),
            'engagement_trends': user_data.get('engagement_history', [])
        }
    
    def design_engagement_experiments(self) -> List[Dict]:
        """エンゲージメント向上実験設計"""
        experiments = [
            {
                'name': 'subject_line_personalization',
                'hypothesis': 'パーソナライズされた件名が開封率を向上させる',
                'variables': ['user_name', 'preferred_categories', 'urgency_indicators'],
                'success_metrics': ['open_rate_improvement', 'engagement_duration'],
                'test_duration': '14_days',
                'sample_size': '1000_users'
            },
            {
                'name': 'content_layout_optimization',
                'hypothesis': 'スキャンしやすいレイアウトがエンゲージメントを向上させる',
                'variables': ['visual_hierarchy', 'white_space', 'typography'],
                'success_metrics': ['scroll_depth', 'time_on_content', 'click_rates'],
                'test_duration': '21_days',
                'sample_size': '1500_users'
            },
            {
                'name': 'delivery_time_optimization',
                'hypothesis': '個人の活動パターンに合わせた配信時間が効果的',
                'variables': ['send_time', 'time_zone', 'user_activity_pattern'],
                'success_metrics': ['immediate_open_rate', 'engagement_depth'],
                'test_duration': '28_days',
                'sample_size': '2000_users'
            }
        ]
        
        return experiments
```

## 使用する技術・ツール
- **分析**: Google Analytics, Mixpanel
- **A/Bテスト**: Optimizely, VWO
- **ユーザビリティ**: Hotjar, Crazy Egg
- **プロトタイピング**: Figma, Adobe XD
- **データ可視化**: D3.js, Chart.js
- **アクセシビリティ**: axe-core, WAVE

## 連携するエージェント
- **NEWS-DevUI**: UI実装連携
- **NEWS-Accessibility**: アクセシビリティ対応
- **NEWS-ReportGen**: ユーザビリティを考慮したレポート設計
- **NEWS-Monitor**: ユーザー行動監視
- **NEWS-L10n**: 多言語UX対応

## KPI目標
- **ユーザビリティスコア**: 4.5/5以上
- **メール開封率**: 30%以上
- **クリック率**: 8%以上
- **ユーザー満足度**: 4.7/5以上
- **タスク完了率**: 90%以上

## UX改善領域

### メールUX
- レスポンシブデザイン
- 読みやすいタイポグラフィ
- 明確な情報階層
- 効果的なCTA配置

### コンテンツUX
- スキャンしやすいレイアウト
- 適切なコンテンツ分割
- 視覚的な重要度表示
- カテゴリ別ナビゲーション

### インタラクションUX
- 直感的なナビゲーション
- フィードバックの明確化
- エラー状態の適切な処理
- アクセシビリティ対応

## ユーザーテスト
- ユーザビリティテスト実行
- A/Bテスト設計・分析
- ユーザーインタビュー
- 行動分析

## 成果物
- UX設計ドキュメント
- ユーザビリティテスト結果
- エンゲージメント最適化プラン
- ユーザージャーニーマップ
- UX改善提案書