"""
MSS-AI Unified Exception Hierarchy
Standardized error handling across all modules
"""

from enum import Enum, auto
from typing import Optional, Dict, Any
import traceback

class ErrorCode(Enum):
    """Standardized error codes for all MSS-AI operations"""
    # System errors (1xxx)
    SYSTEM_UNKNOWN = 1000
    SYSTEM_INIT_FAILED = 1001
    SYSTEM_CONFIG_MISSING = 1002
    SYSTEM_RESOURCE_EXHAUSTED = 1003

    # Model/Inference errors (2xxx)
    MODEL_LOAD_FAILED = 2001
    MODEL_INFERENCE_FAILED = 2002
    MODEL_TIMEOUT = 2003
    MODEL_OUTPUT_INVALID = 2004
    MODEL_NOT_FOUND = 2005

    # Knowledge Base errors (3xxx)
    KB_LOAD_FAILED = 3001
    KB_NODE_NOT_FOUND = 3002
    KB_INVALID_FORMAT = 3003
    KB_CIRCULAR_REFERENCE = 3004

    # Symbolic Engine errors (4xxx)
    SYMBOLIC_INVALID_QUERY = 4001
    SYMBOLIC_CONTRADICTION = 4002
    SYMBOLIC_PATH_NOT_FOUND = 4003
    SYMBOLIC_CYCLE_DETECTED = 4004

    # Post-Process errors (5xxx)
    PP_RULE_INVALID = 5001
    PP_RULE_CONFLICT = 5002
    PP_FILTER_FAILED = 5003

    # Validation errors (6xxx)
    VALIDATION_INPUT_EMPTY = 6001
    VALIDATION_INPUT_TOO_LONG = 6002
    VALIDATION_LAYER_MISMATCH = 6003
    VALIDATION_CONFIDENCE_INVALID = 6004

    # Network/External errors (7xxx)
    NETWORK_TIMEOUT = 7001
    NETWORK_CONNECTION_FAILED = 7002
    API_RATE_LIMITED = 7003

    # Security/Compliance errors (8xxx)
    SECURITY_FORBIDDEN_CONTENT = 8001
    COMPLIANCE_VIOLATION = 8002

class MSSBaseException(Exception):
    """Base exception for all MSS-AI errors"""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.SYSTEM_UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.cause = cause
        self.traceback_str = traceback.format_exc() if cause else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization"""
        return {
            "error": True,
            "code": self.code.value,
            "code_name": self.code.name,
            "message": self.message,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None,
            "traceback": self.traceback_str
        }

    def __str__(self) -> str:
        base = f"[{self.code.name}] {self.message}"
        if self.details:
            base += f" | Details: {self.details}"
        if self.cause:
            base += f" | Caused by: {type(self.cause).__name__}: {self.cause}"
        return base

# Specific exception classes

class SystemException(MSSBaseException):
    """System-level errors"""
    def __init__(self, message: str, code: ErrorCode = ErrorCode.SYSTEM_UNKNOWN, **kwargs):
        super().__init__(message, code=code, **kwargs)

class ModelException(MSSBaseException):
    """Model inference errors"""
    def __init__(self, message: str, code: ErrorCode = ErrorCode.MODEL_INFERENCE_FAILED, **kwargs):
        super().__init__(message, code=code, **kwargs)

class KnowledgeBaseException(MSSBaseException):
    """Knowledge base errors"""
    def __init__(self, message: str, code: ErrorCode = ErrorCode.KB_LOAD_FAILED, **kwargs):
        super().__init__(message, code=code, **kwargs)

class SymbolicEngineException(MSSBaseException):
    """Symbolic reasoning errors"""
    def __init__(self, message: str, code: ErrorCode = ErrorCode.SYMBOLIC_INVALID_QUERY, **kwargs):
        super().__init__(message, code=code, **kwargs)

class PostProcessException(MSSBaseException):
    """Post-processing errors"""
    def __init__(self, message: str, code: ErrorCode = ErrorCode.PP_FILTER_FAILED, **kwargs):
        super().__init__(message, code=code, **kwargs)

class ValidationException(MSSBaseException):
    """Input validation errors"""
    def __init__(self, message: str, code: ErrorCode = ErrorCode.VALIDATION_INPUT_EMPTY, **kwargs):
        super().__init__(message, code=code, **kwargs)

class NetworkException(MSSBaseException):
    """Network/external service errors"""
    def __init__(self, message: str, code: ErrorCode = ErrorCode.NETWORK_TIMEOUT, **kwargs):
        super().__init__(message, code=code, **kwargs)

class SecurityException(MSSBaseException):
    """Security and compliance errors"""
    def __init__(self, message: str, code: ErrorCode = ErrorCode.SECURITY_FORBIDDEN_CONTENT, **kwargs):
        super().__init__(message, code=code, **kwargs)

# Utility functions

def wrap_exception(
    exc: Exception,
    target_class: type = MSSBaseException,
    code: ErrorCode = ErrorCode.SYSTEM_UNKNOWN,
    message: Optional[str] = None
) -> MSSBaseException:
    """Wrap any exception into MSS exception hierarchy"""
    if isinstance(exc, MSSBaseException):
        return exc

    msg = message or str(exc)
    return target_class(
        message=msg,
        code=code,
        cause=exc,
        details={"original_type": type(exc).__name__}
    )

def safe_execute(
    func,
    *args,
    error_code: ErrorCode = ErrorCode.SYSTEM_UNKNOWN,
    error_class: type = MSSBaseException,
    default_return=None,
    **kwargs
):
    """Execute function safely, catching and wrapping exceptions"""
    try:
        return func(*args, **kwargs)
    except MSSBaseException:
        raise
    except Exception as e:
        raise error_class(
            message=f"Operation failed: {str(e)}",
            code=error_code,
            cause=e,
            details={"function": func.__name__}
        )

class ErrorLogger:
    """Centralized error logging with structured output"""

    def __init__(self, module_name: str):
        self.module_name = module_name
        self.error_count = 0
        self.error_history = []

    def log(self, exc: MSSBaseException, context: Optional[Dict] = None):
        """Log an exception with context"""
        self.error_count += 1
        entry = {
            "module": self.module_name,
            "timestamp": __import__('time').time(),
            "error": exc.to_dict(),
            "context": context or {}
        }
        self.error_history.append(entry)

        # Print structured error
        print(f"[ERROR:{self.module_name}] {exc}")
        if exc.traceback_str:
            print(f"[TRACEBACK]\n{exc.traceback_str}")

        return entry

    def get_stats(self) -> Dict:
        """Get error statistics"""
        return {
            "module": self.module_name,
            "total_errors": self.error_count,
            "error_codes": list(set(
                e["error"]["code"] for e in self.error_history
            )),
            "recent_errors": self.error_history[-5:]
        }

# Demo
if __name__ == "__main__":
    print("=" * 60)
    print("MSS Exception Hierarchy Demo")
    print("=" * 60)

    # Demo 1: Basic exception
    try:
        raise ModelException(
            "Inference failed due to timeout",
            code=ErrorCode.MODEL_TIMEOUT,
            details={"model": "qwen2.5:7b", "timeout_ms": 30000}
        )
    except MSSBaseException as e:
        print(f"\n1. Caught: {e}")
        print(f"   Dict: {e.to_dict()}")

    # Demo 2: Wrapped exception
    try:
        try:
            result = 1 / 0
        except Exception as e:
            raise wrap_exception(e, ModelException, ErrorCode.MODEL_INFERENCE_FAILED)
    except MSSBaseException as e:
        print(f"\n2. Wrapped: {e}")

    # Demo 3: Safe execute
    def risky_func(x):
        return 1 / x

    result = safe_execute(
        risky_func,
        0,
        error_code=ErrorCode.SYSTEM_UNKNOWN,
        default_return=None
    )
    print(f"\n3. Safe execute result: {result}")

    # Demo 4: Error logger
    logger = ErrorLogger("test_module")
    try:
        raise ValidationException("Input too long", code=ErrorCode.VALIDATION_INPUT_TOO_LONG)
    except MSSBaseException as e:
        logger.log(e, context={"input_length": 10000})

    print(f"\n4. Logger stats: {logger.get_stats()}")

    print("\n" + "=" * 60)
    print("Demo complete")
