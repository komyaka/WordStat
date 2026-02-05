"""
Кэш для результатов WordStat API
"""
import sqlite3
import json
import threading
import time
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from queue import Queue, Empty

from utils.logger import get_logger
from utils.constants import CACHE_DB_PATH, CACHE_DEFAULT_TTL_DAYS, CACHE_WORKER_INTERVAL_SEC

logger = get_logger('WordStat.Cache')


class WordstatCache:
    """Кэш для результатов API"""
    
    def __init__(self, db_path: str = CACHE_DB_PATH, ttl_days: int = CACHE_DEFAULT_TTL_DAYS):
        """
        Args:
            db_path: Путь к БД кэша
            ttl_days: TTL для кэшированных данных (дни)
        """
        if not isinstance(db_path, str):
            raise TypeError("db_path должен быть строкой")
        if not isinstance(ttl_days, int) or ttl_days < 1:
            raise ValueError("ttl_days должен быть int >= 1")
        
        self.db_path = db_path
        self.ttl_days = ttl_days
        self.ttl_seconds = ttl_days * 24 * 3600
        
        self.db_queue: Queue = Queue()
        self.worker_thread: Optional[threading.Thread] = None
        self.running = False
        
        self._init_db()
        self._start_worker()
        
        logger.info(f"✓ WordstatCache инициализирован (DB: {db_path}, TTL: {ttl_days} дней)")
    
    def _init_db(self):
        """Инициализировать БД"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phrase TEXT UNIQUE NOT NULL,
                    results TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    ttl_seconds INTEGER NOT NULL
                )
            ''')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_phrase ON cache(phrase)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON cache(timestamp)')
            
            conn.commit()
            conn.close()
            
            logger.info(f"✓ БД иници��лизирована: {self.db_path}")
        
        except Exception as e:
            logger.error(f"✗ Ошибка инициализации БД: {e}")
            raise
    
    def _start_worker(self):
        """Запустить рабочий поток для БД"""
        try:
            self.running = True
            self.worker_thread = threading.Thread(
                target=self._db_worker,
                daemon=True,
                name="CacheWorker"
            )
            self.worker_thread.start()
            logger.info("✓ DB worker thread запущен")
        
        except Exception as e:
            logger.error(f"✗ Ошибка запуска worker: {e}")
    
    def _db_worker(self):
        """Рабочий поток для операций с БД"""
        while self.running:
            try:
                # Получить операцию из очереди
                try:
                    operation = self.db_queue.get(timeout=CACHE_WORKER_INTERVAL_SEC)
                except Empty:
                    # Периодическая очистка устаревших данных
                    self._cleanup_expired()
                    continue
                
                if operation is None:
                    break
                
                op_type = operation.get('type')
                
                if op_type == 'set':
                    self._db_set(operation['phrase'], operation['results'])
                elif op_type == 'get':
                    # Игнорируем, так как get синхронный
                    pass
                elif op_type == 'delete':
                    self._db_delete(operation['phrase'])
                elif op_type == 'cleanup':
                    self._cleanup_expired()
            
            except Exception as e:
                logger.error(f"✗ Ошибка в worker: {e}")
    
    def _db_set(self, phrase: str, results: List[Dict]):
        """Установить значение в БД (синхронно)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = time.time()
            results_json = json.dumps(results, ensure_ascii=False)
            
            cursor.execute('''
                INSERT OR REPLACE INTO cache (phrase, results, timestamp, ttl_seconds)
                VALUES (?, ?, ?, ?)
            ''', (phrase, results_json, now, self.ttl_seconds))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"✓ Кэш сохранён: {phrase}")
        
        except Exception as e:
            logger.error(f"✗ Ошибка сохранения кэша: {e}")
    
    def _db_get(self, phrase: str) -> Optional[List[Dict]]:
        """Получить значение из БД"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = time.time()
            
            cursor.execute('''
                SELECT results, timestamp, ttl_seconds FROM cache
                WHERE phrase = ?
            ''', (phrase,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                logger.debug(f"⊘ Кэш не найден: {phrase}")
                return None
            
            results_json, timestamp, ttl_seconds = row
            
            # Проверить TTL
            if now - timestamp > ttl_seconds:
                logger.debug(f"⊘ Кэш истёк: {phrase}")
                self.db_queue.put({'type': 'delete', 'phrase': phrase})
                return None
            
            results = json.loads(results_json)
            logger.debug(f"✓ Кэш найден: {phrase}")
            return results
        
        except Exception as e:
            logger.error(f"✗ Ошибка получения кэша: {e}")
            return None
    
    def _db_delete(self, phrase: str):
        """Удалить из БД"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM cache WHERE phrase = ?', (phrase,))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"✓ Кэш удалён: {phrase}")
        
        except Exception as e:
            logger.error(f"✗ Ошибка удаления кэша: {e}")
    
    def _cleanup_expired(self):
        """Очистить устаревшие записи"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = time.time()
            
            cursor.execute('''
                DELETE FROM cache
                WHERE (? - timestamp) > ttl_seconds
            ''', (now,))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted > 0:
                logger.info(f"🧹 Очистка кэша: удалено {deleted} устаревших записей")
        
        except Exception as e:
            logger.error(f"✗ Ошибка очистки кэша: {e}")
    
    def get(self, phrase: str) -> Optional[List[Dict]]:
        """Получить из кэша"""
        try:
            return self._db_get(phrase)
        except Exception as e:
            logger.error(f"✗ Ошибка get(): {e}")
            return None
    
    def set(self, phrase: str, results: List[Dict]):
        """Установить в кэш"""
        try:
            if not isinstance(phrase, str):
                raise TypeError("phrase должен быть строкой")
            if not isinstance(results, list):
                raise TypeError("results должен быть списком")
            
            self._db_set(phrase, results)
        
        except Exception as e:
            logger.error(f"✗ Ошибка set(): {e}")
    
    def delete(self, phrase: str):
        """Удалить из кэша"""
        try:
            self.db_queue.put({'type': 'delete', 'phrase': phrase})
        except Exception as e:
            logger.error(f"✗ Ошибка delete(): {e}")
    
    def clear(self):
        """Очистить весь кэш"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM cache')
            
            conn.commit()
            conn.close()
            
            logger.info("🧹 Кэш полностью очищен")
        
        except Exception as e:
            logger.error(f"✗ Ошибка clear(): {e}")
    
    def get_stats(self) -> Dict:
        """Получить статистику кэша"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM cache')
            total = cursor.fetchone()[0]
            
            now = time.time()
            cursor.execute('''
                SELECT COUNT(*) FROM cache
                WHERE (? - timestamp) <= ttl_seconds
            ''', (now,))
            valid = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total': total,
                'valid': valid,
                'expired': total - valid,
            }
        
        except Exception as e:
            logger.error(f"✗ Ошибка get_stats(): {e}")
            return {'total': 0, 'valid': 0, 'expired': 0}
    
    def shutdown(self):
        """Завершить работу"""
        try:
            logger.info("🔴 Завершение работы cache...")
            self.running = False
            self.db_queue.put(None)  # Сигнал к завершению
            
            if self.worker_thread:
                self.worker_thread.join(timeout=5)
            
            logger.info("✓ Cache завершен")
        
        except Exception as e:
            logger.error(f"✗ Ошибка shutdown(): {e}")