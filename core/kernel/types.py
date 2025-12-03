"""
Type definitions for the Kernel and Gateway components.

Defines data structures, request/response types, error codes,
and protocol specifications for internal communication.
"""

class Request:
    """
    Base class for all incoming requests to the system.
    
    Attributes:
        - type: Type of request ('chat', 'tool_call', 'plan', 'agent_interaction')
        - message: User-facing message or payload
        - context: Additional information and metadata
        - timestamp: Time when the request was received
    """
    def __init__(self, request_type: str, message: str = None, 
                 context: dict = None, timestamp: float = None):
        self.type = request_type
        self.message = message or ''
        self.context = context or {}
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> dict:
        """
        Convert the request instance to a dictionary for serialization.
        """
        return {
            'type': self.type,
            'message': self.message,
            'context': self.context,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Request':
        """
        Create a request instance from a dictionary.
        """
        return cls(
            request_type=data['type'],
            message=data.get('message'),
            context=data.get('context', {}),
            timestamp=data.get('timestamp')
        )


class Response:
    """
    Base class for all system responses.
    
    Attributes:
        - status: Status of the response ('success', 'error', 'pending')
        - message: Human-readable message
        - result: Optional payload or content
        - timestamp: Time when the response was generated
    """
    def __init__(self, status: str, message: str = None, 
                 result: dict = None, timestamp: float = None):
        self.status = status
        self.message = message or ''
        self.result = result or {}
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> dict:
        """
        Convert the response instance to a dictionary for serialization.
        """
        return {
            'status': self.status,
            'message': self.message,
            'result': self.result,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Response':
        """
        Create a response instance from a dictionary.
        """
        return cls(
            status=data['status'],
            message=data.get('message'),
            result=data.get('result', {}),
            timestamp=data.get('timestamp')
        )


class Error:
    """
    Base class for system errors.
    
    Attributes:
        - code: Error code (e.g., '404', '503')
        - message: Human-readable error message
        - details: Additional information about the error
        - timestamp: Time when the error occurred
    """
    def __init__(self, error_code: str, message: str = None, 
                 details: dict = None, timestamp: float = None):
        self.code = error_code
        self.message = message or ''
        self.details = details or {}
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> dict:
        """
        Convert the error instance to a dictionary for serialization.
        """
        return {
            'code': self.code,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Error':
        """
        Create an error instance from a dictionary.
        """
        return cls(
            error_code=data['code'],
            message=data.get('message'),
            details=data.get('details', {}),
            timestamp=data.get('timestamp')
        )


class RequestType:
    """
    Enum-like class for request types.
    
    Values:
        - CHAT: For user chat interactions
        - TOOL_CALL: For tool usage requests
        - PLAN: For goal decomposition and task planning
        - AGENT_INTERACTION: For agent creation or activation
    """
    CHAT = 'chat'
    TOOL_CALL = 'tool_call'
    PLAN = 'plan'
    AGENT_INTERACTION = 'agent_interaction'