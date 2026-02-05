"""
Обработка ошибок API Wordstat
"""
from enum import Enum
from typing import Optional, Tuple
import time

logger_instance = None


class ErrorType(Enum):
    """Типы ошибок"""
    TIMEOUT = "timeout"
    AUTH_ERROR = "auth_error"
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"
    CLIENT_ERROR = "client_error"
    NETWORK_ERROR = "network_error"
    PARSE_ERROR = "parse_error"
    UNKNOWN = "unknown"


class ErrorAction(Enum):
    """Действия при ошибке"""
    RETRY = "retry"
    BACKOFF = "backoff"
    SKIP = "skip"
    STOP = "stop"


class APIError(Exception):
    """API ошибка"""
    
    def __init__(self,
                 error_type: ErrorType,
                 message: str,
                 status_code: Optional[int] = None,
                 original_exception: Optional[Exception] = None):
        """Инициализация"""
        self.error_type = error_type
        self.message = message
        self.status_code = status_code
        self.original_exception = original_exception
        self.timestamp = time.time()
        
        super().__init__(f"[{error_type.value.upper()}] {message}")


class ErrorHandler:
    """Обработчик ошибок"""
    
    # Маппинг HTTP кодов на типы ошибок
    HTTP_ERROR_MAP = {
        400: ErrorType.CLIENT_ERROR,
        401: ErrorType.AUTH_ERROR,
        403: ErrorType.AUTH_ERROR,
        429: ErrorType.RATE_LIMIT,
        500: ErrorType.SERVER_ERROR,
        502: ErrorType.SERVER_ERROR,
        503: ErrorType.SERVER_ERROR,
        504: ErrorType.TIMEOUT,
    }
    
    # Маппинг типов ошибок на действия
    ERROR_ACTION_MAP = {
        ErrorType.TIMEOUT: ErrorAction.BACKOFF,
        ErrorType.AUTH_ERROR: ErrorAction.STOP,
        ErrorType.RATE_LIMIT: ErrorAction.BACKOFF,
        ErrorType.SERVER_ERROR: ErrorAction.BACKOFF,
        ErrorType.CLIENT_ERROR: ErrorAction.SKIP,
        ErrorType.NETWORK_ERROR: ErrorAction.STOP,
        ErrorType.PARSE_ERROR: ErrorAction.SKIP,
        ErrorType.UNKNOWN: ErrorAction.BACKOFF,
    }
    
    @staticmethod
    def classify_error(status_code: int) -> ErrorType:
        """Классифицировать ошибку по HTTP коду"""
        return ErrorHandler.HTTP_ERROR_MAP.get(status_code, ErrorType.UNKNOWN)
    
    @staticmethod
    def get_action(error_type: ErrorType, attempt: int, max_retries: int) -> ErrorAction:
        """Получить действие для ошибки"""
        base_action = ErrorHandler.ERROR_ACTION_MAP.get(error_type, ErrorAction.BACKOFF)
        
        # Если это последняя попытка, не повторяем
        if attempt >= max_retries - 1 and base_action == ErrorAction.BACKOFF:
            return ErrorAction.SKIP
        
        return base_action
    
    @staticmethod
    def get_backoff_delay(attempt: int) -> float:
        """Получить exponential backoff delay"""
        # 1, 2, 4, 8, 16 сек (с максимумом 60)
        delay = min(2 ** attempt, 60)
        return float(delay)
    
    @staticmethod
    def format_error_message(error: APIError) -> str:
        """Форматировать сообщение об ошибке"""
        return f"[{error.error_type.value}] {error.message}"