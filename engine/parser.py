"""
Главный движок парсинга (ПОЛНЫЙ С DEBUG ЛОГИРОВАНИЕМ)
"""
import threading
import time
import json
from typing import Dict, List, Optional, Set, Tuple
from queue import Queue, Empty
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from utils.logger import get_logger
from utils.constants import (
    MIN_DEPTH, MAX_DEPTH, MIN_TOP_N, MAX_TOP_N,
    UI_UPDATE_INTERVAL_MS, AUTOSAVE_INTERVAL_SEC
)
from storage.models import TaskItem, KeywordData, SessionState, APIResponse
from api.wordstat_client import WordstatClient
from api.error_handler import APIError, ErrorType
from engine.rate_limiter import RateLimiter
from filters.keyword_filters import KeywordFilter
from nlp.normalizer import get_normalizer
from nlp.geo_cleaner import GeoCleaner, GeoMode

logger = get_logger('WordStat.Parser')


class ParsingEngine:
    """Главный движок парсинга"""
    
    def __init__(self,
                 api_client: WordstatClient,
                 rate_limiter: RateLimiter,
                 keyword_filter: KeywordFilter,
                 num_workers: int = 3,
                 cache=None,
                 cache_mode: str = "on"):
        """Инициализация"""
        if not isinstance(api_client, WordstatClient):
            raise TypeError("api_client должен быть WordstatClient")
        if not isinstance(rate_limiter, RateLimiter):
            raise TypeError("rate_limiter должен быть RateLimiter")
        if not isinstance(keyword_filter, KeywordFilter):
            raise TypeError("keyword_filter должен быть KeywordFilter")
        if not isinstance(num_workers, int) or num_workers < 1 or num_workers > 10:
            raise ValueError("num_workers должен быть 1-10")
        
        self.api_client = api_client
        self.rate_limiter = rate_limiter
        self.keyword_filter = keyword_filter
        self.num_workers = num_workers
        
        self.normalizer = get_normalizer()
        self.geo_cleaner: Optional[GeoCleaner] = None
        
        self.state = SessionState()
        self.state_lock = threading.RLock()
        
        self.depth = 2
        self.top_n = 3
        self.num_phrases = 100
        self.regions = None
        self.device = 'all'
        self.geo_mode = GeoMode.OFF
        
        self.task_queue: Queue = Queue()
        self.executor: Optional[ThreadPoolExecutor] = None
        
        self.running = False
        self.paused = False
        self.cache = cache
        self.cache_mode = (cache_mode or "on").lower()
        self.cache_hits = 0
        
        self.ui_callback = None
        self.autosave_callback = None
        self.last_ui_update = 0
        self.last_autosave = 0
        
        logger.info(f"✓ ParsingEngine инициализирован ({self.num_workers} workers)")
    
    def set_parsing_params(self,
                          depth: int,
                          top_n: int,
                          num_phrases: int,
                          regions: Optional[List[int]] = None,
                          device: str = 'all',
                          geo_mode: GeoMode = GeoMode.OFF) -> None:
        """Установить параметры парсинга"""
        if not isinstance(depth, int) or depth < MIN_DEPTH or depth > MAX_DEPTH:
            raise ValueError(f"depth ��олжен быть {MIN_DEPTH}-{MAX_DEPTH}")
        if not isinstance(top_n, int) or top_n < MIN_TOP_N or top_n > MAX_TOP_N:
            raise ValueError(f"top_n должен быть {MIN_TOP_N}-{MAX_TOP_N}")
        if not isinstance(num_phrases, int) or num_phrases < 1 or num_phrases > 2000:
            raise ValueError("num_phrases должен быть 1-2000")
        
        self.depth = depth
        self.top_n = top_n
        self.num_phrases = num_phrases
        self.regions = regions
        self.device = device
        self.geo_mode = geo_mode
        
        if self.geo_mode != GeoMode.OFF and self.geo_cleaner is None:
            self.geo_cleaner = GeoCleaner()
        
        logger.info(f"📋 Параметры: depth={depth}, top_n={top_n}, phrases={num_phrases}")
    
    def set_cache_settings(self, cache, mode: str = "on") -> None:
        """Установить настройки кэша"""
        self.cache = cache
        self.cache_mode = (mode or "on").lower()
        self.cache_hits = 0
        logger.info(f"🧠 Cache settings applied: mode={self.cache_mode}")
    
    def add_seeds(self, seeds_text: str) -> None:
        """Добавить семена"""
        if not isinstance(seeds_text, str):
            raise TypeError("seeds_text должен быть строкой")
        
        logger.info(f"🌱 Добавление семян...")
        
        seeds = []
        for line in seeds_text.split('\n'):
            normalized = self.normalizer.normalize_phrase(line)
            if normalized:
                seeds.append(normalized)
        
        unique_seeds = []
        seen = set()
        for seed in seeds:
            if seed not in seen:
                unique_seeds.append(seed)
                seen.add(seed)
        
        logger.info(f"🌱 Добавлено {len(unique_seeds)} семян (из {len(seeds)})")
        
        with self.state_lock:
            for seed in unique_seeds:
                self._enqueue_task(seed, depth=1, source_phrase=None, seed=seed)
        
        logger.info(f"📦 Задач в очереди: {self.task_queue.qsize()}")
    
    def _enqueue_task(self, phrase: str, depth: int, source_phrase: Optional[str], seed: str) -> None:
        """Добавить задачу в очередь"""
        normalized_phrase = self.normalizer.normalize_phrase(phrase)
        
        if not normalized_phrase:
            logger.debug(f"⊘ Пустая фраза, пропускаю")
            return
        
        task_key = f"{normalized_phrase}|{depth}"
        
        if task_key in self.state.enqueued_phrases:
            logger.debug(f"⊘ '{normalized_phrase}' уже в очереди")
            return
        
        if task_key in self.state.queried_phrases:
            logger.debug(f"⊘ '{normalized_phrase}' уже ��апрошена")
            return
        
        task = TaskItem(
            phrase=normalized_phrase,
            depth=depth,
            seed=seed,
            source=source_phrase
        )
        
        self.task_queue.put(task.to_dict())
        self.state.enqueued_phrases.add(task_key)
        
        logger.debug(f"✓ Задача добавлена: '{normalized_phrase}' (depth={depth})")
    
    def _on_result(self, task: TaskItem, response: APIResponse) -> None:
        """Обработать результат"""
        logger.info(f"📨 Получен результат для '{task.phrase}'")
        
        with self.state_lock:
            task_key = f"{task.phrase}|{task.depth}"
            
            self.state.queried_phrases.add(task_key)
            if task_key in self.state.enqueued_phrases:
                self.state.enqueued_phrases.discard(task_key)
            
            all_results = []
            
            if response.results:
                all_results.extend(response.results)
                logger.info(f"   📊 Results: {len(response.results)}")
            
            if response.associations:
                all_results.extend(response.associations)
                logger.info(f"   🔗 Associations: {len(response.associations)}")
            
            logger.info(f"   📦 Всего: {len(all_results)} результатов")
            
            added_count = 0
            
            for idx, result in enumerate(all_results):
                logger.debug(f"   Обработка результата {idx+1}: {result}")
                
                keyword_phrase = result.get('phrase', '').strip()
                count = result.get('count', 0)
                
                logger.debug(f"   - Фраза: '{keyword_phrase}', Count: {count} (тип: {type(count).__name__})")
                
                if not keyword_phrase or not isinstance(count, int) or count < 0:
                    logger.debug(f"   ⊘ Некорректный результат: phrase='{keyword_phrase}', count={count}")
                    continue
                
                # ✅ Проверка фильтра
                passed, reject_reason = self.keyword_filter.apply(keyword_phrase, count)
                
                if not passed:
                    logger.debug(f"   ⊗ Отфильтрована '{keyword_phrase}': {reject_reason}")
                    continue
                
                logger.info(f"   ✅ ПРОЙДЕНА ФИЛЬТРАЦИЯ: '{keyword_phrase}' (count={count})")
                
                if self.geo_cleaner:
                    processed_phrase, geo_tokens = self.geo_cleaner.process(
                        keyword_phrase,
                        self.geo_mode
                    )
                    
                    if processed_phrase is None:
                        logger.debug(f"   ⊗ Гео-исключена '{keyword_phrase}'")
                        continue
                    
                    keyword_phrase = processed_phrase
                else:
                    geo_tokens = []
                
                keyword_normalized = self.normalizer.normalize_phrase(keyword_phrase)
                
                if keyword_normalized in self.state.keywords:
                    existing = self.state.keywords[keyword_normalized]
                    existing.count = max(existing.count, count)
                    logger.debug(f"   ⟲ Обновлён: '{keyword_normalized}'")
                else:
                    kwd = KeywordData(
                        phrase=keyword_normalized,
                        count=count,
                        seed=task.seed,
                        depth=task.depth,
                        source=task.source,
                        geo_tokens=geo_tokens,
                        timestamp=datetime.now().isoformat(),
                        origin="API"
                    )
                    self.state.keywords[keyword_normalized] = kwd
                    added_count += 1
                    logger.info(f"   ✅ НОВОЕ КЛЮЧЕВОЕ СЛОВО ДОБАВЛЕНО: '{keyword_normalized}' (count={count}, depth={task.depth})")
                
                # Рекурсия для depth > 1
                if task.depth < self.depth:
                    sorted_results = sorted(
                        all_results,
                        key=lambda x: x.get('count', 0),
                        reverse=True
                    )
                    
                    logger.debug(f"   🔄 Рекурсия: добавляю {min(self.top_n, len(sorted_results))} top результатов")
                    
                    for idx_top, top_result in enumerate(sorted_results[:self.top_n]):
                        next_phrase = top_result.get('phrase', '').strip()
                        if next_phrase and idx_top < self.top_n:
                            self._enqueue_task(
                                next_phrase,
                                depth=task.depth + 1,
                                source_phrase=task.phrase,
                                seed=task.seed
                            )
            
            logger.info(f"   📊 ВСЕГО ДОБАВЛЕНО НОВЫХ КЛЮЧЕЙ: {added_count}")
            self.state.completed_requests += 1
    
    def _on_error(self, task: TaskItem, error_msg: str) -> None:
        """Обработать ошибку"""
        logger.error(f"❌ Ошибка для '{task.phrase}': {error_msg}")
        
        with self.state_lock:
            task_key = f"{task.phrase}|{task.depth}"
            self.state.queried_phrases.add(task_key)
            if task_key in self.state.enqueued_phrases:
                self.state.enqueued_phrases.discard(task_key)
    
    def _process_task(self, task_dict: Dict) -> Tuple[Optional[TaskItem], Optional[APIResponse], Optional[str]]:
        """Обработать задачу"""
        try:
            task = TaskItem.from_dict(task_dict)
            logger.debug(f"🔄 Обработка: '{task.phrase}' (depth={task.depth})")
        except Exception as e:
            logger.error(f"✗ Ошибка восстановления задачи: {e}")
            return None, None, str(e)
        
        try:
            use_cache = self.cache and self.cache_mode in ("on", "only", "refresh")
            cached_payload = None
            if use_cache:
                cached_payload = self.cache.get(task.phrase)

            if cached_payload and self.cache_mode in ("on", "only"):
                cached_results = []
                cached_assoc = []
                if isinstance(cached_payload, dict):
                    cached_results = cached_payload.get("results", []) or []
                    cached_assoc = cached_payload.get("associations", []) or []
                elif isinstance(cached_payload, list):
                    cached_results = cached_payload

                if cached_results or cached_assoc:
                    self.cache_hits += 1
                    logger.info(f"📦 Cache hit for '{task.phrase}'")
                    return task, APIResponse(results=cached_results, associations=cached_assoc, status_code=200), None
                if self.cache_mode == "only":
                    logger.info(f"📦 Cache-only mode, no data for '{task.phrase}'")
                    return task, APIResponse(results=[], associations=[], status_code=200), None

            allowed, msg = self.rate_limiter.acquire(timeout=60.0)
            if not allowed:
                error_msg = f"Лимит: {msg}"
                logger.warning(f"⚠ {error_msg}")
                return task, None, error_msg
            
            logger.debug(f"🌐 API запрос для '{task.phrase}'...")
            
            response = self.api_client.get_wordstat(
                phrase=task.phrase,
                num_phrases=self.num_phrases,
                regions=self.regions,
                device=self.device
            )
            
            logger.debug(f"✓ Ответ получен для '{task.phrase}'")

            if self.cache and self.cache_mode in ("on", "refresh"):
                try:
                    self.cache.set(task.phrase, {
                        "results": response.results,
                        "associations": response.associations,
                    })
                except Exception as e:
                    logger.debug(f"⚠ Не удалось сохранить кэш для '{task.phrase}': {e}")

            return task, response, None
        
        except APIError as e:
            error_msg = str(e)
            logger.warning(f"⚠ API Error для '{task.phrase}': {error_msg}")
            return task, None, error_msg
        except Exception as e:
            error_msg = str(e)
            logger.error(f"✗ Неожиданная ошибка для '{task.phrase}': {error_msg}")
            return task, None, error_msg
    
    def start(self) -> None:
        """Запустить парсинг"""
        if self.running:
            logger.warning("⚠ Парсинг уже запущен")
            return
        
        logger.info("=" * 80)
        logger.info("▶ ЗАПУСК ПАРСИНГА")
        logger.info("=" * 80)
        logger.info(f"   Параметры: depth={self.depth}, top_n={self.top_n}, workers={self.num_workers}")
        logger.info(f"   Задач в очереди: {self.task_queue.qsize()}")
        logger.info("=" * 80)
        
        self.running = True
        self.paused = False
        self.state.session_start = time.time()
        
        self.executor = ThreadPoolExecutor(max_workers=self.num_workers, thread_name_prefix="Parser-")
        
        self._main_loop()
    
    def _main_loop(self) -> None:
        """Основной цикл"""
        logger.info("🔄 Основной цикл запущен")
        
        futures = set()
        last_queue_check = time.time()
        
        while self.running:
            if self.paused:
                logger.debug("⏸ На паузе...")
                time.sleep(0.1)
                continue
            
            now = time.time()
            if now - last_queue_check > 0.1 or len(futures) < self.num_workers:
                try:
                    while len(futures) < self.num_workers:
                        task_dict = self.task_queue.get_nowait()
                        future = self.executor.submit(self._process_task, task_dict)
                        futures.add(future)
                        logger.debug(f"📤 Задача отправлена в executor (всего: {len(futures)})")
                except Empty:
                    pass
                
                last_queue_check = now
            
            done_futures = set()
            for future in list(futures):
                if future.done():
                    try:
                        result = future.result(timeout=0)
                        if result:
                            task, response, error = result
                            
                            if error:
                                if task:
                                    self._on_error(task, error)
                            elif response and task:
                                self._on_result(task, response)
                        
                        done_futures.add(future)
                    except Exception as e:
                        logger.error(f"✗ Ошибка обработки результата: {e}")
                        done_futures.add(future)
            
            futures -= done_futures
            
            queue_empty = False
            try:
                queue_empty = self.task_queue.empty()
            except:
                pass
            
            if queue_empty and not futures:
                logger.info("=" * 80)
                logger.info("✓ ВСЕ ЗАДАЧИ ВЫПОЛНЕНЫ!")
                logger.info("=" * 80)
                logger.info(f"   Найдено ключей: {len(self.state.keywords)}")
                logger.info(f"   Выполнено запросов: {self.state.completed_requests}")
                logger.info("=" * 80)
                self.running = False
                break
            
            now = time.time()
            
            if now - self.last_ui_update > (UI_UPDATE_INTERVAL_MS / 1000.0):
                if self.ui_callback:
                    try:
                        with self.state_lock:
                            stats = {
                                'found': len(self.state.keywords),
                                'queue': self.task_queue.qsize(),
                                'requests_done': self.state.completed_requests,
                                'elapsed_sec': now - self.state.session_start,
                                'cache_hits': self.cache_hits,
                            }
                        self.ui_callback(stats)
                    except Exception as e:
                        logger.error(f"✗ Ошибка UI callback: {e}")
                
                self.last_ui_update = now
            
            if now - self.last_autosave > AUTOSAVE_INTERVAL_SEC:
                if self.autosave_callback:
                    try:
                        self.autosave_callback()
                    except Exception as e:
                        logger.error(f"✗ Ошибка автосейва: {e}")
                
                self.last_autosave = now
            
            time.sleep(0.05)
    
    def pause(self) -> None:
        """Пауза"""
        if not self.running or self.paused:
            return
        
        logger.info("⏸ Пауза...")
        self.paused = True
    
    def resume(self) -> None:
        """Возобновить"""
        if not self.running or not self.paused:
            return
        
        logger.info("▶ Возобновление...")
        self.paused = False
    
    def stop(self) -> None:
        """Остановить"""
        if not self.running:
            return
        
        logger.info("⏹ Остановка...")
        self.running = False
        
        if self.executor:
            self.executor.shutdown(wait=True)
        
        logger.info("✓ Парсинг остановлен")
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        with self.state_lock:
            elapsed = time.time() - self.state.session_start
            
            return {
                'found': len(self.state.keywords),
                'queue': self.task_queue.qsize(),
                'requests_done': self.state.completed_requests,
                'elapsed_sec': elapsed,
                'rps_stats': self.rate_limiter.get_stats(),
            }
