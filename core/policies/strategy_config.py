"""
Configuration for policy strategies that optimize planner and tool behavior.

Defines strategy parameters, evaluation criteria, and adjustment rules.
"""

class StrategyConfig:
    """
    Configuration class for defining policy strategies.
    
    Attributes:
        - name: Name of the strategy (e.g., 'adaptive_planning', 'tool_optimization')
        - parameters: Dictionary of parameter values
        - evaluation_criteria: List of metrics used to evaluate strategy performance
        - adjustment_rules: Rules for when and how to adjust parameters
        - active: Boolean indicating if the strategy is currently active
    """
    def __init__(self, name: str, parameters: dict = None, 
                 evaluation_criteria: list = None, 
                 adjustment_rules: dict = None, active: bool = True):
        self.name = name
        self.parameters = parameters or {}
        self.evaluation_criteria = evaluation_criteria or []
        self.adjustment_rules = adjustment_rules or {}
        self.active = active

    def update_parameters(self, new_params: dict) -> None:
        """
        Update the strategy parameters with new values.
        
        Args:
            new_params: Dictionary of parameter updates
        """
        self.parameters.update(new_params)

    def evaluate_performance(self, metrics: dict) -> bool:
        """
        Evaluate if the current strategy is performing well based on criteria.
        
        Args:
            metrics: Dictionary of performance metrics (e.g., success_rate, completion_time)
        
        Returns:
            True if strategy meets evaluation criteria, False otherwise
        """
        for criterion in self.evaluation_criteria:
            if not self._check_criterion(criterion, metrics):
                return False
        return True

    def _check_criterion(self, criterion: dict, metrics: dict) -> bool:
        """
        Check if a specific evaluation criterion is met.
        
        Args:
            criterion: Dictionary with 'metric', 'target_value', and optional 'operator'
            metrics: Dictionary of performance metrics
        
        Returns:
            True if criterion is met, False otherwise
        """
        metric_name = criterion['metric']
        target_value = criterion['target_value']
        operator = criterion.get('operator', '>=')

        value = metrics.get(metric_name)
        
        if value is None:
            return False
        
        if operator == '>=' and value >= target_value:
            return True
        elif operator == '<=' and value <= target_value:
            return True
        elif operator == '==' and value == target_value:
            return True
        elif operator == '>' and value > target_value:
            return True
        elif operator == '<' and value < target_value:
            return True
        
        return False

    def apply_adjustment(self, adjustment: dict) -> None:
        """
        Apply a parameter adjustment based on evaluation results.
        
        Args:
            adjustment: Dictionary of parameters to adjust and their new values
        """
        self.parameters.update(adjustment)

    def get_summary(self) -> str:
        """
        Return a formatted summary of the strategy configuration.
        """
        return (f'Strategy: {self.name}\n'
                f'Parameters: {self.parameters}\n'
                f'Criteria: {self.evaluation_criteria}\n'
                f'Active: {self.active}')
    def activate(self) -> None:
        """
        Activate the strategy.
        """
        self.active = True

    def deactivate(self) -> None:
        """
        Deactivate the strategy.
        """
        self.active = False

    def to_dict(self) -> dict:
        """
        Convert strategy configuration to dictionary.

        Returns:
            Dictionary representation of the strategy
        """
        return {
            'name': self.name,
            'parameters': self.parameters,
            'evaluation_criteria': self.evaluation_criteria,
            'adjustment_rules': self.adjustment_rules,
            'active': self.active
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'StrategyConfig':
        """
        Create a StrategyConfig instance from a dictionary.

        Args:
            data: Dictionary containing strategy configuration

        Returns:
            StrategyConfig instance
        """
        return cls(
            name=data.get('name', 'unnamed_strategy'),
            parameters=data.get('parameters', {}),
            evaluation_criteria=data.get('evaluation_criteria', []),
            adjustment_rules=data.get('adjustment_rules', {}),
            active=data.get('active', True)
        )
