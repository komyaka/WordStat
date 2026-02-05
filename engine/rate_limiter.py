"""
Глобальный rate limiter для контроля RPS и квот (ТРОЙНАЯ ПРОВЕРКА)
"""
import time
import threading
from collections import deque
from typing import Dict, Tuple

from utils.logger import get_logger

logger = get_logger('WordStat.RateLimiter')

class RateLimiter:
    """
    Глобальный rate limiter с поддержкой:
    - RPS (requests per second)
    - Per hour quota
    - Per day quota
    """
    
    def __init__(self,
                 max_rps: int = 10,
                 max_per_hour: int = 10000,
                 max_per_day: int = 1000):
        """
        Args:
            max_rps: Максимум запросов в секунду (глобально)
            max_per_hour: Максимум в час
            max_per_day: Максимум в день
        """
        # ✓ ПРОВЕРКА 1: Валидация параметров
        if max_rps < 1:
            raise ValueError("max_rps должен быть >= 1")
        if max_per_hour < 1:
            raise ValueError("max_per_hour должен быть >= 1")
        if max_per_day < 1:
            raise ValueError("max_per_day должен быть >= 1")
        if max_per_day < max_per_hour:
            raise ValueError("max_per_day не может быть меньше max_per_hour")
        
        self.max_rps = max_rps
        self.max_per_hour = max_per_hour
        self.max_per_day = max_per_day
        
        # Потокобезопасность
        self.lock = threading.RLock()
        
        # RPS tracking (timestamps последних запросов)
        self.rps_window = deque(maxlen=max_rps * 2)
        
        # Hour quota
        self.hour_requests = deque()
        self.hour_window_start = None
        self.hour_count = 0
        
        # Day quota
        self.day_requests = deque()
        self.day_window_start = None
        self.day_count = 0
        
        logger.info(f"RateLimiter инициализирован: RPS={max_rps}, Hour={max_per_hour}, Day={max_per_day}")
    
    def _cleanup_old_timestamps(self) -> None:
        """Удалить старые timestamps из окон"""
        now = time.time()
        
        # ✓ ПРОВЕРКА 2: RPS window очистка
        while self.rps_window and self.rps_window[0] < now - 1.0:
            self.rps_window.popleft()
        
        # ✓ ПРОВЕРКА 3: Hour window очистка (3600 секунд)
        if self.hour_window_start is not None and (now - self.hour_window_start) > 3600.0:
            self.hour_window_start = now
            self.hour_count = 0
            self.hour_requests.clear()
        
        # ✓ ПРОВЕРКА 4: Day window очистка (86400 секунд)
        if self.day_window_start is not None and (now - self.day_window_start) > 86400.0:
            self.day_window_start = now
            self.day_count = 0
            self.day_requests.clear()
    
    def acquire(self, cost: int = 1, timeout: float = 30.0) -> Tuple[bool, str]:
        """
        Ожидать разрешения на запрос (блокирующее)
        
        Args:
            cost: "Стоимость" запроса в RPS
            timeout: Максимум времени ожидания (сек)
        
        Returns:
            (success, message)
        """
        # ✓ ПРОВЕРКА 5: Валидация параметров acquire()
        if cost < 1:
            raise ValueError("cost должен быть >= 1")
        if timeout <= 0:
            raise ValueError("timeout должен быть > 0")
        
        start_time = time.time()
        
        while True:
            with self.lock:
                self._cleanup_old_timestamps()
                
                now = time.time()
                
                # ✓ ПРОВЕРКА 6: Инициализация окон
                if self.hour_window_start is None:
                    self.hour_window_start = now
                if self.day_window_start is None:
                    self.day_window_start = now
                
                # ✓ ПРОВЕРКА 7: Day quota проверка
                if self.day_count + cost > self.max_per_day:
                    msg = f"Дневной лимит исчерпан ({self.day_count}/{self.max_per_day})"
                    logger.warning(f"LIMIT HIT: per_day - {msg}")
                    return False, msg
                
                # ✓ ПРОВЕРКА 8: Hour quota проверка
                if self.hour_count + cost > self.max_per_hour:
                    msg = f"Часовой лимит исчерпан ({self.hour_count}/{self.max_per_hour})"
                    logger.warning(f"LIMIT HIT: per_hour - {msg}")
                    return False, msg
                
                # ✓ ПРОВЕРКА 9: RPS проверка
                if len(self.rps_window) + cost <= self.max_rps:
                    # ✓ Можем выполнить запрос
                    now = time.time()
                    for _ in range(cost):
                        self.rps_window.append(now)
                    
                    self.hour_count += cost
                    self.hour_requests.append((now, cost))
                    
                    self.day_count += cost
                    self.day_requests.append((now, cost))
                    
                    logger.debug(f"✓ Разрешение на запрос (RPS: {len(self.rps_window)}/{self.max_rps}, Hour: {self.hour_count}/{self.max_per_hour}, Day: {self.day_count}/{self.max_per_day})")
                    return True, "OK"
            
            # ✓ ПРОВЕРКА 10: Таймаут проверка
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                msg = f"Таймаут ожидания RPS ({timeout}с)"
                logger.warning(msg)
                return False, msg
            
            # ✓ ПРОВЕРКА 11: Малое время сна для меньшей нагрузки
            time.sleep(0.01)
    
    def get_stats(self) -> Dict:
        """Получить текущую статистику"""
        with self.lock:
            self._cleanup_old_timestamps()
            return {
                'rps_current': len(self.rps_window),
                'rps_max': self.max_rps,
                'hour_count': self.hour_count,
                'hour_max': self.max_per_hour,
                'day_count': self.day_count,
                'day_max': self.max_per_day,
                'hour_remaining': max(0, self.max_per_hour - self.hour_count),
                'day_remaining': max(0, self.max_per_day - self.day_count),
            }
    
    def reset_day(self) -> None:
        """Сбросить дневную квоту (для тестов)"""
        with self.lock:
            self.day_count = 0
            self.day_window_start = time.time()
            self.day_requests.clear()
            logger.info("✓ Дневная квота сброшена")
    
    def reset_hour(self) -> None:
        """Сбросить часовую квоту (для тестов)"""
        with self.lock:
            self.hour_count = 0
            self.hour_window_start = time.time()
            self.hour_requests.clear()
            logger.info("✓ Часовая квота сброшена")