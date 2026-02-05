"""
Логирование с поддержкой callback-ов для UI
"""
import logging
import sys
import threading
from datetime import datetime
from typing import Callable, Optional, List

class UILogger:
    """Логгер с поддержкой UI обновлений"""
    
    def __init__(self, name: str, log_callback: Optional[Callable] = None):
        if not isinstance(name, str) or not name:
            raise ValueError("name должно быть непустой строкой")
        
        self.name = name
        self.log_callback = log_callback
        self.logs: List[dict] = []
        self._logs_lock = threading.RLock()
        
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        self.logger.handlers.clear()
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def set_callback(self, callback: Optional[Callable]) -> None:
        if callback is not None and not callable(callback):
            raise TypeError("callback должен быть callable")
        self.log_callback = callback
    
    def _emit(self, level: str, message: str) -> None:
        if not isinstance(message, str):
            message = str(message)
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        }
        
        with self._logs_lock:
            self.logs.append(log_entry)
            if len(self.logs) > 10000:
                self.logs = self.logs[-10000:]
        
        if self.log_callback:
            try:
                self.log_callback(log_entry)
            except Exception as e:
                print(f"Ошибка callback логирования: {e}")
    
    def debug(self, msg: str) -> None:
        self.logger.debug(msg)
        self._emit('DEBUG', msg)
    
    def info(self, msg: str) -> None:
        self.logger.info(msg)
        self._emit('INFO', msg)
    
    def warning(self, msg: str) -> None:
        self.logger.warning(msg)
        self._emit('WARNING', msg)
    
    def error(self, msg: str) -> None:
        self.logger.error(msg)
        self._emit('ERROR', msg)
    
    def critical(self, msg: str) -> None:
        self.logger.critical(msg)
        self._emit('CRITICAL', msg)

_global_logger: Optional[UILogger] = None
_logger_lock = threading.Lock()

def get_logger(name: str = 'WordStat') -> UILogger:
    global _global_logger
    if _global_logger is None:
        with _logger_lock:
            if _global_logger is None:
                _global_logger = UILogger(name)
    return _global_logger