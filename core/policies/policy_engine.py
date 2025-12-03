"""
Policy Engine for dynamic optimization of system behavior.

Applies policy strategies to adjust planner, tool, and agent parameters based on performance data.
"""

class PolicyEngine:
    """
    Central engine that manages policy strategies and applies them dynamically.
    
    Attributes:
        - strategies: Dictionary of active strategy configurations
        - metrics_source: Reference to the MetricsCollector instance (if available)
        - adjustment_log: List of applied adjustments with rationale
    """
    def __init__(self):
        self.strategies = {}
        self.metrics_source = None
        self.adjustment_log = []

    def register_strategy(self, strategy: 'StrategyConfig') -> None:
        """
        Register a new policy strategy with the engine.
        
        Args:
            strategy: StrategyConfig instance to be registered
        """
        self.strategies[strategy.name] = strategy

    def apply_strategy(self, strategy_name: str) -> bool:
        """
        Apply a specific policy strategy based on its evaluation.
        
        Args:
            strategy_name: Name of the strategy to apply
        
        Returns:
            True if strategy was applied successfully, False otherwise
        """
        if strategy_name not in self.strategies:
            return False
        
        strategy = self.strategies[strategy_name]
        
        # Evaluate performance metrics (simulated for now)
        metrics = self._get_metrics()
        
        if strategy.evaluate_performance(metrics):
            # Apply adjustments if needed
            adjustment = strategy.adjustment_rules.get('adjustment', {})
            if adjustment:
                strategy.apply_adjustment(adjustment)
                self._log_adjustment(strategy_name, adjustment)
            return True
        else:
            return False

    def _get_metrics(self) -> dict:
        """
        Simulate retrieval of performance metrics.
        
        Returns:
            Dictionary of simulated metrics (e.g., success_rate, completion_time)
        """
        return {
            'success_rate': 0.85,
            'completion_time_avg': 120,
            'tool_failure_rate': 0.15,
            'planning_efficiency': 0.92
        }

    def _log_adjustment(self, strategy_name: str, adjustment: dict) -> None:
        """
        Log an applied parameter adjustment.
        
        Args:
            strategy_name: Name of the strategy that made the adjustment
            adjustment: Dictionary of parameters updated and their new values
        """
        self.adjustment_log.append({
            'strategy': strategy_name,
            'adjustments': adjustment,
            'timestamp': self._get_timestamp()
        })

    def get_adjustment_log(self) -> list:
        """
        Return the log of all applied adjustments.
        
        Returns:
            List of logged adjustments
        """
        return self.adjustment_log.copy()

    def _get_timestamp(self) -> str:
        """
        Generate a formatted timestamp.
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_active_strategies(self) -> list:
        """
        Return all currently active strategies.
        
        Returns:
            List of active strategy names
        """
        return list(self.strategies.keys())