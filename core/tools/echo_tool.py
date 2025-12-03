"""
Echo tool for simple message output and debugging.

Provides a basic functionality to return the input message unchanged.
"""

class EchoTool:
    """
    Simple tool that returns the input message unchanged.
    
    Attributes:
        - name: 'echo'
        - description: 'Returns input message as is for debugging and testing purposes'
    """
    def __init__(self):
        self.name = 'echo'
        self.description = 'Returns input message as is for debugging and testing purposes'

    def execute(self, message: str) -> dict:
        """
        Execute the echo operation.
        
        Args:
            message: The message to echo
        
        Returns:
            Dictionary with status and echoed message
        """
        return {
            'status': 'success',
            'message': f'Echoed message: {message}',
            'original_message': message,
            'timestamp': self._get_timestamp()
        }

    def _get_timestamp(self) -> str:
        """
        Generate a formatted timestamp.
        
        Returns:
            Formatted timestamp string
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")