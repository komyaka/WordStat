"""
Рабочий поток для парсинга
"""
import threading
import time
from typing import Optional, Callable
from queue import Queue, Empty

from utils.logger import get_logger
from storage.models import TaskItem, KeywordData
from api.wordstat_client import WordstatClient
from api.error_handler import APIError, ErrorType
from engine.rate_limiter import RateLimiter

logger = get_logger('WordStat.Worker')

class Worker(threading.Thread):
    """Рабочий поток для обработки задач парсинга"""
    
    def __init__(self, 
                 task_queue: Queue, 
                 result_queue: Queue,
                 api_client: WordstatClient,
                 rate_limiter: RateLimiter):
        """
        Args:
            task_queue: Очередь входящих задач
            result_queue: Очередь результатов
            api_client: Клиент API
            rate_limiter: Rate limiter
        """
        super().__init__(daemon=True)
        
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.api_client = api_client
        self.rate_limiter = rate_limiter
        self.running = True
        
        logger.info(f"✓ Worker инициализирован")
    
    def run(self):
        """Основной цикл worker'а"""
        while self.running:
            try:
                # Получить задачу из очереди
                task_dict = self.task_queue.get(timeout=1)
                
                if task_dict is None:
                    break
                
                try:
                    # Восстановить TaskItem
                    task = TaskItem.from_dict(task_dict)
                    
                    # Запросить разрешение у rate limiter
                    allowed, msg = self.rate_limiter.acquire(timeout=60.0)
                    
                    if not allowed:
                        self.result_queue.put({
                            'task': task,
                            'response': None,
                            'error': f"Rate limit: {msg}"
                        })
                        continue
                    
                    # Выполнить запрос
                    response = self.api_client.get_wordstat(
                        phrase=task.phrase,
                        num_phrases=100
                    )
                    
                    self.result_queue.put({
                        'task': task,
                        'response': response,
                        'error': None
                    })
                
                except APIError as e:
                    self.result_queue.put({
                        'task': task,
                        'response': None,
                        'error': str(e)
                    })
                except Exception as e:
                    logger.error(f"✗ Worker ошибка: {e}")
                    self.result_queue.put({
                        'task': task,
                        'response': None,
                        'error': str(e)
                    })
            
            except Empty:
                continue
            except Exception as e:
                logger.error(f"✗ Worker критическая ошибка: {e}")
                time.sleep(0.1)
    
    def stop(self):
        """Остановить worker"""
        self.running = False
        logger.info("✓ Worker остановлен")