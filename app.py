"""
Главное приложение - интеграция всех модулей
"""
import threading
import time
from typing import Optional, Dict
from datetime import datetime

from utils.logger import get_logger
from storage.config_manager import ConfigManager
from storage.state_manager import StateManager
from storage.cache import WordstatCache
from storage.exporter import ExcelExporter
from api.wordstat_client import WordstatClient
from engine.rate_limiter import RateLimiter
from engine.parser import ParsingEngine
from filters.keyword_filters import KeywordFilter
from nlp.geo_cleaner import GeoMode
from ai.clustering import SemanticAnalyzer
from ui.main_window import MainWindow

logger = get_logger('WordStat.App')

class WordStatApp:
    """Главное приложение"""
    
    def __init__(self):
        """Инициализация приложения"""
        
        logger.info("=" * 80)
        logger.info("SEO Wordstat Master AI v.2026 - ИНИЦИАЛИЗАЦИЯ")
        logger.info("=" * 80)
        
        try:
            self.config_manager = ConfigManager()
            self.config = self.config_manager.config
            logger.info("✓ ConfigManager инициализирован")
        except Exception as e:
            logger.critical(f"✗ Ошибка загрузки конфига: {e}")
            raise
        
        try:
            self.state_manager = StateManager()
            logger.info("✓ StateManager инициализирован")
        except Exception as e:
            logger.critical(f"✗ Ошибка инициализации StateManager: {e}")
            raise
        
        try:
            cache_ttl = int(self.config.get('cache', {}).get('ttl_days', 7))
            cache_ttl = max(cache_ttl, 1)
            self.cache_mode = self.config.get('cache', {}).get('mode', 'on')
            self.cache = WordstatCache(ttl_days=cache_ttl)
            logger.info("✓ WordstatCache инициализирован")
        except Exception as e:
            logger.critical(f"✗ Ошибка инициализации Cache: {e}")
            raise
        
        try:
            api_key = self.config.get('api', {}).get('key', '')
            folder_id = self.config.get('api', {}).get('folder_id', '')
            
            if not api_key or not folder_id:
                logger.warning("⚠ API Key или Folder ID не установлены в конфиге")
            
            self.api_client = WordstatClient(api_key or 'temp', folder_id or 'temp')
            logger.info("✓ WordstatClient инициализирован")
        except Exception as e:
            logger.critical(f"✗ Ошибка инициализации API: {e}")
            raise
        
        try:
            max_rps = self.config.get('quotas', {}).get('max_rps', 10)
            max_hour = self.config.get('quotas', {}).get('max_per_hour', 10000)
            max_day = self.config.get('quotas', {}).get('max_per_day', 1000)
            
            self.rate_limiter = RateLimiter(max_rps, max_hour, max_day)
            logger.info("✓ RateLimiter инициализирован")
        except Exception as e:
            logger.critical(f"✗ Ошибка инициализации RateLimiter: {e}")
            raise
        
        try:
            self.keyword_filter = KeywordFilter()
            self._apply_filter_settings()
            logger.info("✓ KeywordFilter инициализирован")
        except Exception as e:
            logger.critical(f"✗ Ошибка инициализации KeywordFilter: {e}")
            raise
        
        try:
            num_workers = self.config.get('parsing', {}).get('workers', 3)
            self.parser = ParsingEngine(
                self.api_client,
                self.rate_limiter,
                self.keyword_filter,
                num_workers=num_workers,
                cache=self.cache,
                cache_mode=self.cache_mode
            )
            logger.info("✓ ParsingEngine инициализирован")
        except Exception as e:
            logger.critical(f"✗ Ошибка инициализации ParsingEngine: {e}")
            raise
        
        try:
            self.analyzer = SemanticAnalyzer(
                lemmatize=self.config.get('ai', {}).get('lemmatize', True),
                max_features=self.config.get('ai', {}).get('max_features', 1000),
                embedding_model=self.config.get('ai', {}).get('embedding_model', 'multilingual'),
                use_semantic=self.config.get('ai', {}).get('use_semantic', True)
            )
            logger.info("✓ SemanticAnalyzer инициализирован")
        except Exception as e:
            logger.critical(f"✗ Ошибка инициализации SemanticAnalyzer: {e}")
            raise
        
        try:
            self.exporter = ExcelExporter()
            logger.info("✓ ExcelExporter инициализирован")
        except Exception as e:
            logger.critical(f"✗ Ошибка инициализации ExcelExporter: {e}")
            raise
        
        try:
            self.ui = MainWindow()
            logger.info("✓ MainWindow инициализирован")
        except Exception as e:
            logger.critical(f"✗ Ошибка инициализации UI: {e}")
            raise
        
        # ✅ УСТАНОВИТЬ ВСЕ CALLBACKS
        self.ui.on_start_callback = self._on_ui_start
        self.ui.on_pause_callback = self._on_ui_pause
        self.ui.on_resume_callback = self._on_ui_resume
        self.ui.on_stop_callback = self._on_ui_stop
        self.ui.on_export_callback = self._on_ui_export
        self.ui.on_ai_analyze_callback = self._on_ai_analyze
        self.ui.on_ai_export_callback = self._on_ai_export
        self.ui.on_apply_filters_callback = self._on_apply_filters
        
        # ✅ ХРАНЕНИЕ РЕЗУЛЬТАТОВ КЛАСТЕРИЗАЦИИ
        self._last_clusters = {}
        
        # ✅ УСТАНОВИТЬ CALLBACKS В PARSER
        self.parser.ui_callback = self._on_parser_update
        self.parser.autosave_callback = self._on_autosave
        self.ui_dispatch = self.ui.post_to_ui
        
        self._load_config_to_ui()

        # ✅ ПЕРИОДИЧЕСКИЙ АВТОСЕЙВ (каждые 60 секунд)
        self._autosave_interval = int(
            self.config.get('autosave', {}).get('interval_sec', 60)
        )
        self._autosave_stop = threading.Event()
        self._autosave_thread = threading.Thread(
            target=self._periodic_autosave_loop,
            daemon=True,
            name="AutosaveThread"
        )
        self._autosave_thread.start()

        # ✅ СОХРАНИТЬ КОНФИГ ПРИ ЗАКРЫТИИ ОКНА
        self.ui.protocol("WM_DELETE_WINDOW", self._on_window_close)

        logger.info("✓ WordStatApp полностью инициализирована")
    
    def _apply_filter_settings(self) -> None:
        """Применить настройки фильтров из конфига"""
        try:
            filters_config = self.config.get('filters', {})
            
            self.keyword_filter.set_min_count(filters_config.get('min_count', 1))
            self.keyword_filter.set_word_range(
                filters_config.get('min_words', 1),
                filters_config.get('max_words', 10)
            )
            
            include_regex = filters_config.get('include_regex', '')
            if include_regex:
                self.keyword_filter.set_include_regex(include_regex)
            
            exclude_regex = filters_config.get('exclude_regex', '')
            if exclude_regex:
                self.keyword_filter.set_exclude_regex(exclude_regex)
            
            exclude_substrings = filters_config.get('exclude_substrings', '')
            if exclude_substrings:
                self.keyword_filter.set_exclude_substrings(exclude_substrings)
            
            minus_words = filters_config.get('minus_words', '')
            if minus_words:
                self.keyword_filter.set_minus_words(
                    minus_words,
                    filters_config.get('minus_word_mode', 'any')
                )
        except Exception as e:
            logger.warning(f"⚠ Ошибка применения фильтров: {e}")
    
    def _load_config_to_ui(self) -> None:
        """Загрузить конфиг в UI"""
        try:
            settings = {
                'api_key': self.config.get('api', {}).get('key', ''),
                'folder_id': self.config.get('api', {}).get('folder_id', ''),
                'depth': self.config.get('parsing', {}).get('depth', 2),
                'top_n': self.config.get('parsing', {}).get('top_n', 3),
                'num_phrases': self.config.get('parsing', {}).get('num_phrases', 100),
                'max_rps': self.config.get('quotas', {}).get('max_rps', 10),
                'max_hour': self.config.get('quotas', {}).get('max_per_hour', 10000),
                'max_day': self.config.get('quotas', {}).get('max_per_day', 1000),
                'cache_mode': self.config.get('cache', {}).get('mode', 'on'),
                'cache_ttl_days': self.config.get('cache', {}).get('ttl_days', 7),
            }
            self.ui.set_settings(settings)
            
            # Load filter settings
            filter_settings = self.config.get('filters', {})
            self.ui.set_filter_settings(filter_settings)
        except Exception as e:
            logger.warning(f"⚠ Ошибка загрузки конфига в UI: {e}")
    
    def _save_config_from_ui(self) -> None:
        """Сохранить конфиг из UI"""
        try:
            settings = self.ui.get_settings()
            
            self.config['api']['key'] = settings.get('api_key', '')
            self.config['api']['folder_id'] = settings.get('folder_id', '')
            self.config['parsing']['depth'] = settings.get('depth', 2)
            self.config['parsing']['top_n'] = settings.get('top_n', 3)
            self.config['parsing']['num_phrases'] = settings.get('num_phrases', 100)
            self.config['quotas']['max_rps'] = settings.get('max_rps', 10)
            self.config['quotas']['max_per_hour'] = settings.get('max_hour', 10000)
            self.config['quotas']['max_per_day'] = settings.get('max_day', 1000)
            self.config['cache']['mode'] = settings.get('cache_mode', 'on')
            self.config['cache']['ttl_days'] = settings.get('cache_ttl_days', 7)
            
            # Save filter settings
            filter_settings = self.ui.get_filter_settings()
            self.config['filters']['min_count'] = filter_settings.get('min_count', 10)
            self.config['filters']['min_words'] = filter_settings.get('min_words', 1)
            self.config['filters']['max_words'] = filter_settings.get('max_words', 10)
            self.config['filters']['include_regex'] = filter_settings.get('include_regex', '')
            self.config['filters']['exclude_regex'] = filter_settings.get('exclude_regex', '')
            self.config['filters']['exclude_substrings'] = filter_settings.get('exclude_substrings', '')
            self.config['filters']['minus_words'] = filter_settings.get('minus_words', '')
            self.config['filters']['minus_word_mode'] = filter_settings.get('minus_word_mode', 'any')
            
            self.config_manager.save()
            logger.info("✓ Конфиг сохранён")
        except Exception as e:
            logger.error(f"✗ Ошибка сохранения конфига: {e}")

    def _apply_cache_settings(self, settings: Dict) -> None:
        """Применить настройки кэша к runtime"""
        try:
            cache_mode = (settings.get('cache_mode', 'on') or 'on').lower()
            ttl_days = int(settings.get('cache_ttl_days', 7) or 7)
            ttl_days = max(ttl_days, 1)

            if cache_mode.lower() == 'off':
                if getattr(self, 'cache', None):
                    self.cache.shutdown()
                self.cache = None
            else:
                should_recreate = not (getattr(self, 'cache', None) and getattr(self.cache, 'ttl_days', None) == ttl_days)
                if should_recreate:
                    if getattr(self, 'cache', None):
                        self.cache.shutdown()
                    self.cache = WordstatCache(ttl_days=ttl_days)

            self.cache_mode = cache_mode
            if hasattr(self.parser, 'set_cache_settings'):
                self.parser.set_cache_settings(self.cache, cache_mode)
            logger.info(f"✓ Настройки кэша применены (mode={cache_mode}, ttl={ttl_days})")
        except Exception as e:
            logger.error(f"✗ Ошибка применения настроек кэша: {e}")
    
    def _on_ui_start(self, seeds: str) -> None:
        """Callback: Запуск парсинга"""
        logger.info("▶ Запуск парсинга...")
        
        try:
            self._save_config_from_ui()
            
            filter_settings = self.ui.get_filter_settings()
            self.keyword_filter.set_min_count(filter_settings.get('min_count', 1))
            self.keyword_filter.set_word_range(
                filter_settings.get('min_words', 1),
                filter_settings.get('max_words', 10)
            )
            
            if filter_settings.get('include_regex'):
                self.keyword_filter.set_include_regex(filter_settings.get('include_regex'))
            if filter_settings.get('exclude_regex'):
                self.keyword_filter.set_exclude_regex(filter_settings.get('exclude_regex'))
            if filter_settings.get('exclude_substrings'):
                self.keyword_filter.set_exclude_substrings(filter_settings.get('exclude_substrings'))
            if filter_settings.get('minus_words'):
                self.keyword_filter.set_minus_words(
                    filter_settings.get('minus_words'),
                    filter_settings.get('minus_word_mode', 'any')
                )
            
            settings = self.ui.get_settings()
            self.parser.set_parsing_params(
                depth=settings.get('depth', 2),
                top_n=settings.get('top_n', 3),
                num_phrases=settings.get('num_phrases', 100),
                geo_mode=GeoMode.OFF
            )
            self._apply_cache_settings(settings)
            
            self.api_client.api_key = settings.get('api_key', '')
            self.api_client.folder_id = settings.get('folder_id', '')
            self.api_client.headers['Authorization'] = f"Api-Key {self.api_client.api_key}"
            
            self.parser.add_seeds(seeds)
            
            # ✅ ЗАПУСТИТЬ ПАРСИНГ В ОТДЕЛЬНОМ ПОТОКЕ
            parser_thread = threading.Thread(target=self._parser_thread_wrapper, daemon=False)
            parser_thread.start()
        
        except Exception as e:
            logger.error(f"✗ Ошибка запуска парсинга: {e}")
            self.ui.set_status(f"❌ Ошибка: {e}")
    
    def _parser_thread_wrapper(self):
        """Обёртка для потока парсинга - отследить завершение"""
        try:
            logger.info("🚀 Парсинг начался в отдельном потоке")
            self.ui_dispatch(self.ui.set_status, "▶ Работает...")
            
            self.parser.start()
            
            logger.info("✓ Парсинг завершился")
            
            # ✅ АВТОМАТИЧЕСКИ ВЫЗВАТЬ STOP CALLBACK
            time.sleep(0.5)
            if self.parser.state.keywords:
                logger.info("🎯 Парсинг завершён, обновляю UI...")
                self.ui_dispatch(self._on_ui_stop)
            else:
                self.ui_dispatch(self.ui.set_status, "⚠ Нет результатов")
        
        except Exception as e:
            logger.error(f"✗ Ошибка в потоке парсинга: {e}")
            self.ui_dispatch(self.ui.set_status, f"❌ Ошибка: {e}")
    
    def _on_ui_pause(self) -> None:
        """Callback: Пауза"""
        logger.info("⏸ Пауза...")
        self.ui.set_status("⏸ На паузе")
        self.parser.pause()
    
    def _on_ui_resume(self) -> None:
        """Callback: Возобновление"""
        logger.info("▶ Возобновление...")
        self.ui.set_status("▶ Продолжение...")
        self.parser.resume()
    
    def _on_ui_stop(self) -> None:
        """Callback: Остановка (ВЫЗЫВАЕТСЯ АВТО��АТИЧЕСКИ ПОСЛЕ ПАРСИНГА)"""
        logger.info("⏹ ОСТАНОВКА И ОБНОВЛЕНИЕ UI...")
        
        try:
            # ✅ ОСТАНОВИТЬ ПАРСИНГ
            if self.parser.running:
                self.parser.stop()
            
            logger.info(f"📊 Получаю результаты: {len(self.parser.state.keywords)} ключей")
            
            # ✅ СОХРАНИТЬ РЕЗУЛЬТАТЫ В FILES
            logger.info("💾 Сохраняю результаты в файлы...")
            self._on_autosave()
            
            # ✅ ОБНОВИТЬ UI - ОТОБРАЗИТЬ РЕЗУЛЬТАТЫ
            time.sleep(0.2)
            
            logger.info("📋 Отображаю результаты в UI таблице...")
            if hasattr(self.ui, 'display_keywords'):
                with self.parser.state_lock:
                    keywords_copy = dict(self.parser.state.keywords)
                
                self.ui.display_keywords(keywords_copy)
            
            # ✅ ОБНОВИТЬ СТАТИСТИКУ
            stats = self.parser.get_stats()
            if hasattr(self.ui, 'update_stats'):
                self.ui.update_stats(stats)
            
            # ✅ УСТАНОВИТЬ ФИНАЛЬНЫЙ СТАТУС
            if hasattr(self.ui, 'set_status'):
                self.ui.set_status(f"✓ Завершено: {len(self.parser.state.keywords)} ключей найдено")
                logger.info("✓ Статус установлен: Завершено")
            
            logger.info("✓ UI полностью обновлен")
        
        except Exception as e:
            logger.error(f"✗ Ошибка при остановке: {e}")
            self.ui.set_status(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_ui_export(self, mode: str) -> None:
        """Callback: Экспорт"""
        logger.info(f"💾 Экспорт ({mode})...")
        
        try:
            keywords = self.parser.state.keywords
            
            if mode == 'seo':
                self.exporter.export_seo_core(keywords, output_path="output_seo_core.xlsx")
            elif mode == 'ppc':
                self.exporter.export_ppc_context(keywords, output_path="output_ppc_context.xlsx")
            elif mode == 'content':
                self.exporter.export_content_plan(keywords, output_path="output_content_plan.xlsx")
            
            self.ui.set_status(f"✓ Экспорт завершён")
        except Exception as e:
            logger.error(f"✗ Ошибка экспорта: {e}")
            self.ui.set_status(f"❌ Ошибка экспорта: {e}")
    
    def _on_ai_analyze(self, settings: Dict) -> None:
        """Callback: AI анализ"""
        logger.info("🤖 Запуск AI анализа...")
        
        try:
            if not self.parser.state.keywords:
                logger.warning("⚠ Нет ключевых слов для анализа")
                self.ui.set_status("⚠ Сначала запустите парсинг")
                return
            
            logger.info(f"📊 Анализирую {len(self.parser.state.keywords)} ключевых слов...")
            self.ui.set_status("🤖 AI анализ в процессе...")
            
            # ✅ ЗАПУСТИТЬ АНАЛИЗ В ОТДЕЛЬНОМ ПОТОКЕ
            ai_thread = threading.Thread(
                target=self._ai_thread_wrapper,
                args=(settings,),
                daemon=False
            )
            ai_thread.start()
        
        except Exception as e:
            logger.error(f"✗ Ошибка AI анализа: {e}")
            self.ui.set_status(f"❌ Ошибка: {e}")
    
    def _ai_thread_wrapper(self, settings: Dict):
        """Обёртка для потока AI анализа"""
        try:
            logger.info("🚀 AI анализ начался в отдельном потоке")

            # ✅ СБРОСИТЬ ПРОГРЕСС-БАР В НАЧАЛЕ
            self.ui_dispatch(self.ui.update_ai_progress, 0, "Запуск анализа...")

            def _progress_cb(pct: int, msg: str) -> None:
                self.ui_dispatch(self.ui.update_ai_progress, pct, msg)

            # ✅ ЗАПУСТИТЬ КЛАСТЕРИЗАЦИЮ
            clusters = self.analyzer.analyze(
                self.parser.state.keywords,
                threshold=settings.get('threshold', 0.5),
                n_clusters=settings.get('n_clusters', 10),
                clustering_mode=settings.get('clustering_mode', 'threshold'),
                min_cluster_size=2,  # Минимум 2 ключа в кластере
                progress_callback=_progress_cb
            )
            
            logger.info(f"✓ AI анализ завершён: {len(clusters)} кластеров")
            
            # ✅ СОХРАНИТЬ РЕЗУЛЬТАТЫ ДЛЯ ЭКСПОРТА
            self._last_clusters = clusters
            
            # ✅ ПОЛУЧИТЬ СТАТИСТИКУ
            stats = self.analyzer.get_cluster_stats(clusters)
            
            # ✅ ФОРМАТИРОВАТЬ РЕЗУЛЬТАТЫ
            results_text = self.analyzer.format_clusters(clusters)
            
            clustering_method = stats.get('clustering_method', 'unknown')
            stats_text = f"""
📊 СТАТИСТИКА КЛАСТЕРИЗАЦИИ
{'=' * 50}
Метод: {clustering_method}
Всего кластеров: {stats.get('total_clusters', 0)}
Всего ключевых слов: {stats.get('total_keywords', 0)}
Средний размер кластера: {stats.get('avg_cluster_size', 0):.1f}
Максимальный размер: {stats.get('max_cluster_size', 0)}
Минимальный размер: {stats.get('min_cluster_size', 0)}
            """
            
            # ✅ ОТОБРАЗИТЬ РЕЗУЛЬТАТЫ
            if hasattr(self.ui, 'display_ai_results'):
                self.ui_dispatch(self.ui.display_ai_results, results_text, stats_text)
            
            self.ui_dispatch(
                self.ui.set_status,
                f"✓ AI анализ завершён: {len(clusters)} кластеров ({clustering_method})"
            )
            
            logger.info("✓ Результаты отображены в UI")
        
        except Exception as e:
            logger.error(f"✗ Ошибка в потоке AI: {e}")
            self.ui_dispatch(self.ui.set_status, f"❌ Ошибка AI: {e}")
            self.ui_dispatch(self.ui.update_ai_progress, 0, f"Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_ai_export(self) -> None:
        """Callback: Экспорт AI анализа"""
        logger.info("💾 Экспорт AI анализа...")
        
        try:
            if not self._last_clusters:
                logger.warning("⚠ Нет результатов кластеризации для экспорта")
                self.ui.set_status("⚠ Сначала запустите AI анализ")
                return
            
            # Экспорт в Excel
            success = self.exporter.export_ai_clusters(
                self._last_clusters,
                keywords=self.parser.state.keywords,
                output_path="output_ai_clusters.xlsx"
            )
            
            if success:
                self.ui.set_status("✓ AI кластеры экспортированы в output_ai_clusters.xlsx")
            else:
                self.ui.set_status("❌ Ошибка экспорта AI кластеров")
        
        except Exception as e:
            logger.error(f"✗ Ошибка экспорта AI: {e}")
            self.ui.set_status(f"❌ Ошибка экспорта: {e}")
    
    def _on_parser_update(self, stats: Dict) -> None:
        """Callback: Обновление статистики (периодический)"""
        try:
            self.ui_dispatch(self.ui.update_stats, stats)
        except Exception as e:
            logger.debug(f"⚠ Ошибка обновления UI: {e}")
    
    def _on_autosave(self) -> None:
        """Callback: Автосейв - СОХРАНИТЬ В FILES"""
        try:
            logger.info(f"💾 Сохраняю состояние: {len(self.parser.state.keywords)} ключей")
            
            with self.parser.state_lock:
                # ✅ СОХРАНИТЬ STATE JSON
                self.state_manager.save_state(self.parser.state)
                
                # ✅ СОХРАНИТЬ TSV
                self.state_manager.save_tsv(self.parser.state.keywords)
            
            logger.info("✓ Состояние сохранено в файлы")
        
        except Exception as e:
            logger.error(f"✗ Ошибка автосейва: {e}")
            import traceback
            traceback.print_exc()

    def _periodic_autosave_loop(self) -> None:
        """Фоновый поток: периодически сохраняет результаты парсинга"""
        logger.info(f"⏰ Периодический автосейв запущен (интервал {self._autosave_interval}с)")
        while not self._autosave_stop.wait(self._autosave_interval):
            try:
                if self.parser.state.keywords:
                    logger.info("⏰ Периодический автосейв...")
                    self._on_autosave()
            except Exception as e:
                logger.error(f"✗ Ошибка периодического автосейва: {e}")
        logger.info("⏰ Периодический автосейв остановлен")

    def _on_apply_filters(self) -> None:
        """Callback: Применить фильтры к уже полученным данным"""
        logger.info("🔧 Применяю фильтры к существующим данным...")
        try:
            filter_settings = self.ui.get_filter_settings()

            # Обновить keyword_filter из UI
            self.keyword_filter.set_min_count(filter_settings.get('min_count', 1))
            self.keyword_filter.set_word_range(
                filter_settings.get('min_words', 1),
                filter_settings.get('max_words', 10)
            )
            if filter_settings.get('include_regex'):
                self.keyword_filter.set_include_regex(filter_settings.get('include_regex'))
            else:
                self.keyword_filter.set_include_regex('')
            if filter_settings.get('exclude_regex'):
                self.keyword_filter.set_exclude_regex(filter_settings.get('exclude_regex'))
            else:
                self.keyword_filter.set_exclude_regex('')
            self.keyword_filter.set_exclude_substrings(
                filter_settings.get('exclude_substrings', '')
            )
            minus_words = filter_settings.get('minus_words', '')
            minus_mode = filter_settings.get('minus_word_mode', 'any')
            if minus_words:
                self.keyword_filter.set_minus_words(minus_words, minus_mode)
            else:
                self.keyword_filter.minus_words = []

            with self.parser.state_lock:
                all_kw = dict(self.parser.state.keywords)

            filtered = {}
            for phrase, kwd in all_kw.items():
                passed, _ = self.keyword_filter.apply(kwd.phrase, kwd.count)
                if passed:
                    filtered[phrase] = kwd

            logger.info(f"🔧 Фильтр: {len(all_kw)} → {len(filtered)} ключей")
            self.ui.display_keywords(filtered)
            self.ui.set_status(f"✓ Фильтр применён: {len(filtered)} из {len(all_kw)} ключей")

        except Exception as e:
            logger.error(f"✗ Ошибка применения фильтров: {e}")
            self.ui.set_status(f"❌ Ошибка фильтрации: {e}")
            import traceback
            traceback.print_exc()

    def _on_window_close(self) -> None:
        """Обработчик закрытия окна — сохранить конфиг и завершить"""
        logger.info("🚪 Закрытие окна...")
        try:
            self._autosave_stop.set()
        except Exception as e:
            logger.warning(f"⚠ Ошибка остановки autosave потока: {e}")
        try:
            self._save_config_from_ui()
            logger.info("✓ Конфиг сохранён при закрытии")
        except Exception as e:
            logger.error(f"✗ Ошибка сохранения конфига при закрытии: {e}")
        try:
            self.ui.destroy()
        except Exception as e:
            logger.error(f"✗ Ошибка destroy: {e}")
            import sys
            sys.exit(0)

    def run(self) -> None:
        """Запустить приложение"""
        try:
            logger.info("🚀 Запуск UI...")
            self.ui.mainloop()
        
        except KeyboardInterrupt:
            logger.info("⏹ Прервано пользователем")
        except Exception as e:
            logger.critical(f"✗ Критическая ошибка: {e}")
        
        finally:
            logger.info("Завершение работы...")
            
            try:
                if self.parser.running:
                    self.parser.stop()
            except:
                pass
            
            try:
                self.cache.shutdown()
            except:
                pass
            
            logger.info("✓ Приложение завершено")

def main():
    """Точка входа"""
    try:
        app = WordStatApp()
        app.run()
    except Exception as e:
        logger.critical(f"✗ Критическая ошибка инициализации: {e}")
        raise

if __name__ == '__main__':
    main()
