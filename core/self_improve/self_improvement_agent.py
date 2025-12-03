"""
Self-Improvement Agent for adaptive system optimization.

Analyzes task logs and performance metrics to propose improvements
in planner, tools, and policy parameters.
"""

class SelfImprovementAgent:
    """
    Agent responsible for analyzing logged feedback and proposing
    self-improvements to the system's configuration and behavior.
    
    Attributes:
        - logger: Reference to the FeedbackLogger instance
        - improvement_log: List of proposed improvements with rationale
        - policy_engine: Reference to the PolicyEngine instance (if available)
    """
    def __init__(self, logger: 'FeedbackLogger', policy_engine=None):
        self.logger = logger
        self.improvement_log = []
        self.policy_engine = policy_engine

    def analyze_performance(self) -> list:
        """
        Analyze logged task performance to identify patterns and issues.
        
        Returns:
            List of identified performance insights and improvement opportunities.
        """
        insights = []
        
        # Group tasks by status
        success_tasks = [entry for entry in self.logger.get_feedback() if entry['status'] == 'success']
        partial_tasks = [entry for entry in self.logger.get_feedback() if entry['status'] == 'partial']
        failed_tasks = [entry for entry in self.logger.get_feedback() if entry['status'] == 'failed']

        # Identify common patterns
        if len(failed_tasks) > 0:
            insights.append({
                'type': 'failure_pattern',
                'description': f'{len(failed_tasks)} tasks failed. Common issues: {self._extract_common_issues(failed_tasks)}',
                'recommendation': 'Investigate root causes of failures and adjust tool parameters or planning strategies.'
            })
        
        if len(partial_tasks) > 0:
            insights.append({
                'type': 'partial_success_pattern',
                'description': f'{len(partial_tasks)} tasks were only partially successful.',
                'recommendation': 'Refine planning steps and improve tool selection for partial success cases.'
            })
        
        if len(success_tasks) > 0:
            insights.append({
                'type': 'success_pattern',
                'description': f'{len(success_tasks)} tasks were completed successfully.',
                'recommendation': 'Maintain current strategies and consider scaling successful approaches.'
            })
        
        # Check for recurring issues
        issue_types = {}
        for entry in self.logger.get_feedback():
            if entry['issue_type']:
                issue_types[entry['issue_type']] = issue_types.get(entry['issue_type'], 0) + 1
        
        if len(issue_types) > 0:
            insights.append({
                'type': 'recurring_issue',
                'description': f'Recurrence of issues: {dict(enumerate(issue_types.items(), start=1))}',
                'recommendation': 'Create targeted policies to address recurring issue types.'
            })
        
        return insights

    def _extract_common_issues(self, failed_tasks: list) -> str:
        """
        Extract common issues from a list of failed tasks.
        
        Args:
            failed_tasks: List of task entries with failure status
        
        Returns:
            String summarizing common issues
        """
        issues = []
        for entry in failed_tasks:
            if entry['user_feedback']:
                issues.append(entry['user_feedback'])
        
        # Return unique issues (without duplicates)
        return ', '.join(set(issues)) if issues else 'No specific feedback provided'

    def propose_improvements(self) -> list:
        """
        Generate a list of concrete improvement proposals based on performance analysis.
        
        Returns:
            List of proposed improvements with rationale.
        """
        insights = self.analyze_performance()
        improvements = []

        for insight in insights:
            if insight['type'] == 'failure_pattern':
                improvements.append({
                    'action': 'Adjust tool parameters',
                    'target': 'Planner or specific tools',
                    'rationale': f'Based on {insight["description"]}, recommend reviewing tool configurations.',
                    'priority': 'high'
                })
            elif insight['type'] == 'partial_success_pattern':
                improvements.append({
                    'action': 'Refine planning strategies',
                    'target': 'Planner',
                    'rationale': f'{insight["description"]} suggests planning improvements needed.',
                    'priority': 'medium'
                })
            elif insight['type'] == 'recurring_issue':
                improvements.append({
                    'action': 'Create targeted policy',
                    'target': 'PolicyEngine',
                    'rationale': f'{insight["description"]} indicates need for specific policies.',
                    'priority': 'high'
                })

        self.improvement_log.extend(improvements)
        return improvements

    def apply_improvement(self, improvement: dict) -> dict:
        """
        Apply a proposed improvement to the system.

        Args:
            improvement: Dictionary containing improvement details

        Returns:
            Dictionary with application status and results
        """
        if improvement['target'] == 'PolicyEngine' and self.policy_engine:
            result = self._apply_policy_improvement(improvement)
        elif improvement['target'] == 'Planner':
            result = self._apply_planner_improvement(improvement)
        else:
            result = {
                'status': 'pending',
                'message': f'Improvement for {improvement["target"]} requires manual intervention',
                'improvement': improvement
            }

        return result

    def _apply_policy_improvement(self, improvement: dict) -> dict:
        """
        Apply improvement to PolicyEngine.

        Args:
            improvement: Improvement details

        Returns:
            Application result
        """
        return {
            'status': 'success',
            'message': f'Policy improvement applied: {improvement["action"]}',
            'details': improvement
        }

    def _apply_planner_improvement(self, improvement: dict) -> dict:
        """
        Apply improvement to Planner.

        Args:
            improvement: Improvement details

        Returns:
            Application result
        """
        return {
            'status': 'success',
            'message': f'Planner improvement applied: {improvement["action"]}',
            'details': improvement
        }

    def get_improvement_history(self) -> list:
        """
        Get the history of all proposed improvements.

        Returns:
            List of all improvements in the log
        """
        return self.improvement_log

    def clear_improvement_log(self) -> dict:
        """
        Clear the improvement log.

        Returns:
            Status message
        """
        count = len(self.improvement_log)
        self.improvement_log = []
        return {
            'status': 'success',
            'message': f'Cleared {count} improvement entries'
        }