'''Policy optimization layer using RL-light methods for adaptive strategy adjustment'''

from typing import Dict, Any, List
import json
from datetime import datetime

class PolicyOptimizationLayer:
    def __init__(self):
        self.reward_schema = {
            'user_satisfaction': 0.4,
            'task_completion_rate': 0.3,
            'agent_efficiency': 0.2,
            'planner_accuracy': 0.1
        }
        self.optimization_history = []

    def calculate_reward(self, task_metrics: Dict[str, Any]) -> float:
        """Calculate the weighted reward based on performance metrics."""
        total_reward = 0.0
        for metric_name, weight in self.reward_schema.items():
            if metric_name in task_metrics:
                value = task_metrics[metric_name]
                total_reward += weight * value
        
        return total_reward

    def evaluate_policy(self, policy: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a policy against performance metrics."""
        reward = self.calculate_reward(metrics)
        
        if reward >= 0.85:
            evaluation = 'excellent'
        elif reward >= 0.75:
            evaluation = 'good'
        else:
            evaluation = 'needs_improvement'
        
        result = {
            'policy': policy['name'],
            'reward': reward,
            'evaluation': evaluation,
            'timestamp': datetime.now().isoformat()
        }
        
        self.optimization_history.append(result)
        return result

    def propose_update(self, policy: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Propose an updated version of the policy based on evaluation."""
        if metrics['task_completion_rate'] < 0.9:
            return {
                'action': 'increase_planner_timeout',
                'description': 'Task completion rate is below target.',
                'confidence': 0.85
            }
        elif metrics['user_satisfaction'] < 0.8:
            return {
                'action': 'enhance_explanation_depth',
                'description': 'User satisfaction with responses is declining.',
                'confidence': 0.75
            }
        else:
            return {
                'action': 'maintain_current_policy',
                'description': 'Policy performance is stable and meets targets.',
                'confidence': 1.0
            }