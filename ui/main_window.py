"""
Главное окно приложения (ПОЛНЫЙ С КНОПКАМИ И AI АНАЛИЗОМ)
"""
import customtkinter as ctk
from typing import Optional, Callable, Dict
import threading
import json
from datetime import datetime

from utils.logger import get_logger
from utils.constants import DEVICE_TYPES, GEO_MODES, CACHE_MODES
from .styles import AppTheme, UIConfig
from .widgets import LabeledEntry, LabeledTextbox, StatCard, LogTable
from .clipboard_handler import ClipboardHandler

logger = get_logger('WordStat.UI')

# ✅ УСТАНОВИТЬ ТЕМУ
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MainWindow(ctk.CTk):
    """Главное окно приложения"""
    
    def __init__(self):
        """Инициализация"""
        super().__init__()
        
        self.title("🔍 SEO Wordstat Master AI v.2026")
        self.geometry(f"{UIConfig.WINDOW_WIDTH}x{UIConfig.WINDOW_HEIGHT}")
        
        # ✅ УСТАНОВИТЬ МИНИМАЛЬНЫЙ РАЗМЕР
        self.minsize(1200, 800)
        
        # ✅ CALLBACKS
        self.on_start_callback: Optional[Callable] = None
        self.on_pause_callback: Optional[Callable] = None
        self.on_resume_callback: Optional[Callable] = None
        self.on_stop_callback: Optional[Callable] = None
        self.on_export_callback: Optional[Callable] = None
        self.on_ai_analyze_callback: Optional[Callable] = None
        
        self.status_label = None
        self.keywords_table = None
        
        self._create_ui()
        
        # ✅ ГОРЯЧИЕ КЛАВИШИ
        self.bind("<Control-s>", lambda e: logger.info("💾 Ctrl+S - сохранение (при остановке)"))
        
        logger.info("✓ MainWindow инициализирован")
    
    def _create_ui(self):
        """Создать UI"""
        # ✅ ГЛАВНЫЙ КОНТЕЙНЕР
        main_frame = ctk.CTkFrame(self, fg_color=UIConfig.BG_PRIMARY)
        main_frame.pack(fill='both', expand=True, padx=0, pady=0)
        
        # ✅ ЗАГОЛОВОК С С��АТУСОМ
        header_frame = ctk.CTkFrame(main_frame, fg_color=UIConfig.BG_SECONDARY, height=60)
        header_frame.pack(fill='x', padx=0, pady=0)
        header_frame.pack_propagate(False)
        
        title = ctk.CTkLabel(
            header_frame,
            text="🔍 SEO Wordstat Master AI v.2026",
            font=UIConfig.FONT_TITLE,
            text_color=UIConfig.COLOR_INFO
        )
        title.pack(side='left', padx=20, pady=10)
        
        self.status_label = ctk.CTkLabel(
            header_frame,
            text="🟢 Готово",
            font=UIConfig.FONT_HEADER,
            text_color=UIConfig.COLOR_SUCCESS
        )
        self.status_label.pack(side='right', padx=20, pady=10)
        
        # ✅ ОСНОВНОЙ КОНТЕНТ (TABS)
        self.tabview = ctk.CTkTabview(main_frame, fg_color=UIConfig.BG_SECONDARY)
        self.tabview.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.tab_parsing = self.tabview.add("📊 Парсинг")
        self.tab_filters = self.tabview.add("🔧 Фильтры")
        self.tab_ai = self.tabview.add("🤖 AI Анализ")
        self.tab_settings = self.tabview.add("⚙️ Настройки")
        
        self._create_tab_parsing()
        self._create_tab_filters()
        self._create_tab_ai()
        self._create_tab_settings()
        
        # ✅ КНОПКИ ВНИЗУ (ОТДЕЛЬНЫЙ ФРЕЙМ)
        buttons_frame = ctk.CTkFrame(main_frame, fg_color=UIConfig.BG_SECONDARY, height=80)
        buttons_frame.pack(fill='x', padx=10, pady=10)
        buttons_frame.pack_propagate(False)
        
        self.btn_start = ctk.CTkButton(
            buttons_frame,
            text="▶ Запуск",
            command=self._on_start,
            fg_color=UIConfig.COLOR_SUCCESS,
            text_color=UIConfig.TEXT_PRIMARY,
            font=UIConfig.FONT_NORMAL,
            height=40,
            width=120
        )
        self.btn_start.pack(side='left', padx=5, pady=20)
        
        self.btn_pause = ctk.CTkButton(
            buttons_frame,
            text="⏸ Пауза",
            command=self._on_pause,
            fg_color=UIConfig.COLOR_WARNING,
            text_color=UIConfig.TEXT_PRIMARY,
            font=UIConfig.FONT_NORMAL,
            height=40,
            width=120
        )
        self.btn_pause.pack(side='left', padx=5, pady=20)
        
        self.btn_resume = ctk.CTkButton(
            buttons_frame,
            text="▶ Продолжить",
            command=self._on_resume,
            fg_color=UIConfig.COLOR_INFO,
            text_color=UIConfig.TEXT_PRIMARY,
            font=UIConfig.FONT_NORMAL,
            height=40,
            width=120
        )
        self.btn_resume.pack(side='left', padx=5, pady=20)
        
        self.btn_stop = ctk.CTkButton(
            buttons_frame,
            text="⏹ Стоп",
            command=self._on_stop,
            fg_color=UIConfig.COLOR_ERROR,
            text_color=UIConfig.TEXT_PRIMARY,
            font=UIConfig.FONT_NORMAL,
            height=40,
            width=120
        )
        self.btn_stop.pack(side='left', padx=5, pady=20)
        
        self.btn_export = ctk.CTkButton(
            buttons_frame,
            text="📊 Экспорт",
            command=self._on_export,
            fg_color=UIConfig.COLOR_INFO,
            text_color=UIConfig.TEXT_PRIMARY,
            font=UIConfig.FONT_NORMAL,
            height=40,
            width=120
        )
        self.btn_export.pack(side='left', padx=5, pady=20)
    
    def _create_tab_parsing(self):
        """Создать вкладку Парсинг"""
        container = ctk.CTkFrame(self.tab_parsing, fg_color=UIConfig.BG_PRIMARY)
        container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # ✅ ЛЕВАЯ ЧАСТЬ - ВВОД
        left_frame = ctk.CTkFrame(container, fg_color=UIConfig.BG_PRIMARY)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        label = ctk.CTkLabel(
            left_frame,
            text="📝 Исходные ключевые слова (семена)",
            font=UIConfig.FONT_HEADER,
            text_color=UIConfig.TEXT_PRIMARY
        )
        label.pack(anchor='w', pady=(0, 10))
        
        self.seeds_textbox = LabeledTextbox(
            left_frame,
            label_text="",
            height=150
        )
        self.seeds_textbox.pack(fill='both', expand=True)
        
        # ✅ ПРАВАЯ ЧАСТЬ - СТАТИСТИКА
        right_frame = ctk.CTkFrame(container, fg_color=UIConfig.BG_SECONDARY, width=250)
        right_frame.pack(side='right', fill='both', expand=False, padx=(10, 0))
        right_frame.pack_propagate(False)
        
        stats_title = ctk.CTkLabel(
            right_frame,
            text="📊 Статистика",
            font=UIConfig.FONT_HEADER,
            text_color=UIConfig.COLOR_INFO
        )
        stats_title.pack(anchor='w', padx=10, pady=10)
        
        self.found_label = StatCard(right_frame, "✓ Найдено ключей", "0")
        self.found_label.pack(fill='x', padx=5, pady=5)
        
        self.queue_label = StatCard(right_frame, "📦 В очереди", "0")
        self.queue_label.pack(fill='x', padx=5, pady=5)
        
        self.requests_label = StatCard(right_frame, "🌐 Запросов", "0")
        self.requests_label.pack(fill='x', padx=5, pady=5)
        
        self.time_label = StatCard(right_frame, "⏱️ Прошло", "00:00:00")
        self.time_label.pack(fill='x', padx=5, pady=5)
        
        self.cache_label = StatCard(right_frame, "💾 Cache Hits", "0")
        self.cache_label.pack(fill='x', padx=5, pady=5)
        
        # ✅ ТАБЛИЦА РЕЗУЛЬТАТОВ
        table_label = ctk.CTkLabel(
            self.tab_parsing,
            text="📋 Найденные ключевые слова:",
            font=UIConfig.FONT_HEADER,
            text_color=UIConfig.TEXT_PRIMARY
        )
        table_label.pack(anchor='w', padx=10, pady=(10, 5))
        
        self.keywords_table = LogTable(self.tab_parsing, max_rows=1000)
        self.keywords_table.pack(fill='both', expand=True, padx=10, pady=(0, 10))
    
    def _create_tab_filters(self):
        """Создать вкладку Фильтры"""
        container = ctk.CTkScrollableFrame(self.tab_filters, fg_color=UIConfig.BG_PRIMARY)
        container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # ✅ МИНИМАЛЬНОЕ КОЛИЧЕСТВО
        self.filter_min_count = LabeledEntry(
            container,
            label_text="🔢 Мин. Count:",
            placeholder="10"
        )
        self.filter_min_count.pack(fill='x', pady=5)
        
        # ✅ ДИАПАЗОН СЛОВ
        words_frame = ctk.CTkFrame(container, fg_color=UIConfig.BG_PRIMARY)
        words_frame.pack(fill='x', pady=5)
        
        self.filter_min_words = LabeledEntry(
            words_frame,
            label_text="📊 Мин. слов:",
            placeholder="1"
        )
        self.filter_min_words.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        self.filter_max_words = LabeledEntry(
            words_frame,
            label_text="📊 Макс. слов:",
            placeholder="10"
        )
        self.filter_max_words.pack(side='left', fill='x', expand=True)
        
        # ✅ REGEX ФИЛЬТРЫ
        self.filter_include_regex = LabeledEntry(
            container,
            label_text="✅ Include Regex:",
            placeholder=""
        )
        self.filter_include_regex.pack(fill='x', pady=5)
        
        self.filter_exclude_regex = LabeledEntry(
            container,
            label_text="❌ Exclude Regex:",
            placeholder=""
        )
        self.filter_exclude_regex.pack(fill='x', pady=5)
        
        # ✅ ИСКЛЮЧАЮЩИЕ ПОДСТРОКИ
        self.filter_exclude_substrings = LabeledTextbox(
            container,
            label_text="🚫 Исключать подстроки:",
            height=80
        )
        self.filter_exclude_substrings.pack(fill='both', expand=True, pady=5)
        
        # ✅ МИНУС-СЛОВА
        self.filter_minus_words = LabeledTextbox(
            container,
            label_text="➖ Минус-слова:",
            height=80
        )
        self.filter_minus_words.pack(fill='both', expand=True, pady=5)
        
        self.filter_minus_mode = LabeledEntry(
            container,
            label_text="⚙️ Режим минус-слов (all/any):",
            placeholder="any"
        )
        self.filter_minus_mode.pack(fill='x', pady=5)
    
    def _create_tab_ai(self):
        """Создать вкладку AI"""
        container = ctk.CTkScrollableFrame(self.tab_ai, fg_color=UIConfig.BG_PRIMARY)
        container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # ✅ ПАРАМЕТРЫ АНАЛИЗА
        params_frame = ctk.CTkFrame(container, fg_color=UIConfig.BG_SECONDARY)
        params_frame.pack(fill='x', padx=5, pady=10)
        
        params_label = ctk.CTkLabel(
            params_frame,
            text="⚙️ Параметры AI анализа",
            font=UIConfig.FONT_HEADER,
            text_color=UIConfig.COLOR_INFO
        )
        params_label.pack(anchor='w', padx=10, pady=(10, 5))
        
        self.ai_lemmatize = LabeledEntry(
            params_frame,
            label_text="📚 Лемматизация (True/False):",
            placeholder="True"
        )
        self.ai_lemmatize.pack(fill='x', pady=5, padx=10)
        
        self.ai_max_features = LabeledEntry(
            params_frame,
            label_text="🎯 Max Features:",
            placeholder="1000"
        )
        self.ai_max_features.pack(fill='x', pady=5, padx=10)
        
        self.ai_clustering_mode = LabeledEntry(
            params_frame,
            label_text="🔗 Режим кластеризации (threshold/fixed):",
            placeholder="threshold"
        )
        self.ai_clustering_mode.pack(fill='x', pady=5, padx=10)
        
        self.ai_threshold = LabeledEntry(
            params_frame,
            label_text="📏 Порог сходства (0-1):",
            placeholder="0.5"
        )
        self.ai_threshold.pack(fill='x', pady=5, padx=10)
        
        self.ai_n_clusters = LabeledEntry(
            params_frame,
            label_text="🎁 Количество кластеров:",
            placeholder="10"
        )
        self.ai_n_clusters.pack(fill='x', pady=5, padx=10)
        
        # ✅ КНОПКА ЗАПУСКА АНАЛИЗА
        button_frame = ctk.CTkFrame(container, fg_color=UIConfig.BG_PRIMARY)
        button_frame.pack(fill='x', padx=5, pady=10)
        
        self.btn_ai_analyze = ctk.CTkButton(
            button_frame,
            text="🤖 Запустить AI анализ",
            command=self._on_ai_analyze,
            fg_color=UIConfig.COLOR_INFO,
            text_color=UIConfig.TEXT_PRIMARY,
            font=UIConfig.FONT_NORMAL,
            height=40
        )
        self.btn_ai_analyze.pack(side='left', padx=5, pady=10, fill='x', expand=True)
        
        # ✅ РЕЗУЛЬТАТЫ АНАЛИЗА
        results_label = ctk.CTkLabel(
            container,
            text="📊 Результаты анализа:",
            font=UIConfig.FONT_HEADER,
            text_color=UIConfig.COLOR_INFO
        )
        results_label.pack(anchor='w', padx=5, pady=(20, 10))
        
        self.ai_results_textbox = ctk.CTkTextbox(
            container,
            font=UIConfig.FONT_MONO,
            height=300
        )
        self.ai_results_textbox.pack(fill='both', expand=True, padx=5, pady=5)
        
        # ✅ СТАТИСТИКА
        stats_label = ctk.CTkLabel(
            container,
            text="📈 Статистика кластеров:",
            font=UIConfig.FONT_HEADER,
            text_color=UIConfig.COLOR_INFO
        )
        stats_label.pack(anchor='w', padx=5, pady=(10, 5))
        
        self.ai_stats_textbox = ctk.CTkTextbox(
            container,
            font=UIConfig.FONT_NORMAL,
            height=100
        )
        self.ai_stats_textbox.pack(fill='x', padx=5, pady=5)
    
    def _create_tab_settings(self):
        """Создать вкладку Настройки"""
        container = ctk.CTkScrollableFrame(self.tab_settings, fg_color=UIConfig.BG_PRIMARY)
        container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # ✅ API
        api_label = ctk.CTkLabel(
            container,
            text="🔑 API Yandex Cloud",
            font=UIConfig.FONT_HEADER,
            text_color=UIConfig.COLOR_INFO
        )
        api_label.pack(anchor='w', pady=(0, 10))
        
        self.settings_api_key = LabeledEntry(
            container,
            label_text="🔐 API Key:",
            placeholder="AQVNy..."
        )
        self.settings_api_key.pack(fill='x', pady=5)
        
        self.settings_folder_id = LabeledEntry(
            container,
            label_text="📁 Folder ID:",
            placeholder="b1234..."
        )
        self.settings_folder_id.pack(fill='x', pady=5)
        
        # ✅ ПАРСИНГ
        parsing_label = ctk.CTkLabel(
            container,
            text="⚙️ Параметры парсинга",
            font=UIConfig.FONT_HEADER,
            text_color=UIConfig.COLOR_INFO
        )
        parsing_label.pack(anchor='w', pady=(20, 10))
        
        self.settings_depth = LabeledEntry(
            container,
            label_text="🔄 Глубина (1-3):",
            placeholder="2"
        )
        self.settings_depth.pack(fill='x', pady=5)
        
        self.settings_top_n = LabeledEntry(
            container,
            label_text="⭐ Top N (1-5):",
            placeholder="3"
        )
        self.settings_top_n.pack(fill='x', pady=5)
        
        self.settings_num_phrases = LabeledEntry(
            container,
            label_text="📝 Кол-во фраз (1-100):",
            placeholder="100"
        )
        self.settings_num_phrases.pack(fill='x', pady=5)
        
        # ✅ КВОТЫ
        quota_label = ctk.CTkLabel(
            container,
            text="⚡ Квоты и Rate Limit",
            font=UIConfig.FONT_HEADER,
            text_color=UIConfig.COLOR_INFO
        )
        quota_label.pack(anchor='w', pady=(20, 10))
        
        self.settings_max_rps = LabeledEntry(
            container,
            label_text="🚀 Max RPS:",
            placeholder="10"
        )
        self.settings_max_rps.pack(fill='x', pady=5)
        
        self.settings_max_hour = LabeledEntry(
            container,
            label_text="⏰ Max за час:",
            placeholder="10000"
        )
        self.settings_max_hour.pack(fill='x', pady=5)
        
        self.settings_max_day = LabeledEntry(
            container,
            label_text="📅 Max за день:",
            placeholder="1000"
        )
        self.settings_max_day.pack(fill='x', pady=5)
        
        # ✅ CACHE
        cache_label = ctk.CTkLabel(
            container,
            text="💾 Cache",
            font=UIConfig.FONT_HEADER,
            text_color=UIConfig.COLOR_INFO
        )
        cache_label.pack(anchor='w', pady=(20, 10))
        
        self.settings_cache_mode = LabeledEntry(
            container,
            label_text="🔄 Режим кэша (on/off/only/refresh):",
            placeholder="on"
        )
        self.settings_cache_mode.pack(fill='x', pady=5)
        
        self.settings_cache_ttl = LabeledEntry(
            container,
            label_text="🕐 TTL кэша (дни):",
            placeholder="7"
        )
        self.settings_cache_ttl.pack(fill='x', pady=5)
    
    def _on_start(self):
        """Кнопка Запуск"""
        logger.info("▶ Клик по кнопке Запуск")
        seeds = self.seeds_textbox.get()
        
        if not seeds.strip():
            logger.warning("⚠ Семена пусты")
            self.set_status("❌ Ошибка: пусты семена")
            return
        
        if self.on_start_callback:
            try:
                self.set_status("⏳ Запуск...")
                self.on_start_callback(seeds)
            except Exception as e:
                logger.error(f"✗ Ошибка callback: {e}")
                self.set_status(f"❌ Ошибка: {e}")
    
    def _on_pause(self):
        """Кнопка Пауза"""
        logger.info("⏸ Клик по кнопке Пауза")
        if self.on_pause_callback:
            try:
                self.set_status("⏸ На паузе")
                self.on_pause_callback()
            except Exception as e:
                logger.error(f"✗ Ошибка callback: {e}")
    
    def _on_resume(self):
        """Кнопка Продолжить"""
        logger.info("▶ Клик по кнопке Продолжить")
        if self.on_resume_callback:
            try:
                self.set_status("▶ Продолжение...")
                self.on_resume_callback()
            except Exception as e:
                logger.error(f"✗ Ошибка callback: {e}")
    
    def _on_stop(self):
        """Кнопка Стоп"""
        logger.info("⏹ Клик по кнопке Стоп")
        if self.on_stop_callback:
            logger.info("📞 Вызываю on_stop_callback")
            try:
                self.set_status("⏹ Остановка...")
                self.on_stop_callback()
            except Exception as e:
                logger.error(f"✗ Ошибка callback: {e}")
                self.set_status(f"❌ Ошибка: {e}")
        else:
            logger.warning("⚠ on_stop_callback не установлен")
    
    def _on_export(self):
        """Кнопка Экспорт"""
        logger.info("📊 Клик по кнопке Экспорт")
        if self.on_export_callback:
            try:
                self.set_status("💾 Экспорт...")
                self.on_export_callback('seo')
                self.set_status("✓ Экспорт завершён")
            except Exception as e:
                logger.error(f"✗ Ошибка callback: {e}")
                self.set_status(f"❌ Ошибка экспорта: {e}")
    
    def _on_ai_analyze(self):
        """Кнопка AI анализ"""
        logger.info("🤖 Клик по кнопке AI анализ")
        
        if hasattr(self, 'on_ai_analyze_callback') and self.on_ai_analyze_callback:
            try:
                settings = self.get_ai_settings()
                logger.info(f"📋 AI settings: {settings}")
                self.on_ai_analyze_callback(settings)
            except Exception as e:
                logger.error(f"✗ Ошибка callback: {e}")
                self.set_status(f"❌ Ошибка: {e}")
        else:
            logger.warning("⚠ on_ai_analyze_callback не установлен")
    
    def update_stats(self, stats: Dict):
        """Обновить статистику"""
        try:
            self.found_label.set_value(str(stats.get('found', 0)))
            self.queue_label.set_value(str(stats.get('queue', 0)))
            self.requests_label.set_value(str(stats.get('requests_done', 0)))
            
            elapsed = stats.get('elapsed_sec', 0)
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            self.time_label.set_value(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            
            self.update()
        except Exception as e:
            logger.error(f"✗ Ошибка update_stats: {e}")
    
    def set_status(self, status: str):
        """Установить статус"""
        try:
            if self.status_label is None:
                logger.warning("⚠ status_label не инициализирован")
                return
            
            self.status_label.configure(text=status)
            
            if "Завершено" in status or "✓" in status:
                self.status_label.configure(text_color=UIConfig.COLOR_SUCCESS)
            elif "Ошибка" in status or "❌" in status:
                self.status_label.configure(text_color=UIConfig.COLOR_ERROR)
            elif "Работ��ет" in status or "▶" in status or "AI анализ" in status:
                self.status_label.configure(text_color=UIConfig.COLOR_WARNING)
            elif "Пауза" in status or "⏸" in status:
                self.status_label.configure(text_color=UIConfig.COLOR_WARNING)
            
            logger.info(f"✓ Статус: {status}")
            self.update()
        except Exception as e:
            logger.error(f"✗ Ошибка set_status: {e}")
    
    def display_keywords(self, keywords: Dict):
        """Отобразить ключевые слова"""
        try:
            if not hasattr(self, 'keywords_table') or self.keywords_table is None:
                logger.warning("⚠ Таблица ключевых слов не инициализирована")
                return
            
            logger.info(f"📋 Отображаю {len(keywords)} ключевых слов")
            
            self.keywords_table.clear()
            
            sorted_kw = sorted(keywords.values(), key=lambda k: k.count, reverse=True)
            
            for idx, kwd in enumerate(sorted_kw[:500]):
                try:
                    self.keywords_table.add_row(
                        phrase=kwd.phrase,
                        count=str(kwd.count),
                        source=kwd.source or kwd.origin or "API",
                        depth=str(kwd.depth),
                        seed=kwd.seed,
                        timestamp=kwd.timestamp
                    )
                except Exception as e:
                    logger.debug(f"⚠ Ошибка добавления строки: {e}")
            
            logger.info(f"✓ Таблица обновлена: {min(len(sorted_kw), 500)} строк")
            self.update()
        
        except Exception as e:
            logger.error(f"✗ Ошибка display_keywords: {e}")
            import traceback
            traceback.print_exc()
    
    def display_ai_results(self, results_text: str, stats_text: str = ""):
        """Отобразить результаты AI анализа"""
        try:
            if not hasattr(self, 'ai_results_textbox'):
                logger.warning("⚠ AI results textbox не инициализирован")
                return
            
            logger.info("📊 Отображаю результаты AI анализа")
            
            self.ai_results_textbox.delete("1.0", "end")
            self.ai_results_textbox.insert("1.0", results_text)
            
            if hasattr(self, 'ai_stats_textbox') and stats_text:
                self.ai_stats_textbox.delete("1.0", "end")
                self.ai_stats_textbox.insert("1.0", stats_text)
            
            self.update()
            logger.info("✓ Результаты AI анализа отображены")
        
        except Exception as e:
            logger.error(f"✗ Ошибка display_ai_results: {e}")
            import traceback
            traceback.print_exc()
    
    def get_settings(self) -> Dict:
        """Получить настройки"""
        try:
            return {
                'api_key': self.settings_api_key.get() or '',
                'folder_id': self.settings_folder_id.get() or '',
                'depth': int(self.settings_depth.get() or 2),
                'top_n': int(self.settings_top_n.get() or 3),
                'num_phrases': int(self.settings_num_phrases.get() or 100),
                'max_rps': int(self.settings_max_rps.get() or 10),
                'max_hour': int(self.settings_max_hour.get() or 10000),
                'max_day': int(self.settings_max_day.get() or 1000),
            }
        except Exception as e:
            logger.error(f"✗ Ошибка get_settings: {e}")
            return {
                'api_key': '',
                'folder_id': '',
                'depth': 2,
                'top_n': 3,
                'num_phrases': 100,
                'max_rps': 10,
                'max_hour': 10000,
                'max_day': 1000,
            }
    
    def get_filter_settings(self) -> Dict:
        """Получить настройки фильтров"""
        try:
            return {
                'min_count': int(self.filter_min_count.get() or 1),
                'min_words': int(self.filter_min_words.get() or 1),
                'max_words': int(self.filter_max_words.get() or 10),
                'include_regex': self.filter_include_regex.get() or '',
                'exclude_regex': self.filter_exclude_regex.get() or '',
                'exclude_substrings': self.filter_exclude_substrings.get() or '',
                'minus_words': self.filter_minus_words.get() or '',
                'minus_word_mode': self.filter_minus_mode.get() or 'any',
            }
        except Exception as e:
            logger.error(f"✗ Ошибка get_filter_settings: {e}")
            return {}
    
    def get_ai_settings(self) -> Dict:
        """Получить AI настройки"""
        try:
            lemmatize_str = self.ai_lemmatize.get() or 'True'
            lemmatize = lemmatize_str.lower() == 'true'
            
            return {
                'lemmatize': lemmatize,
                'max_features': int(self.ai_max_features.get() or 1000),
                'clustering_mode': self.ai_clustering_mode.get() or 'threshold',
                'threshold': float(self.ai_threshold.get() or 0.5),
                'n_clusters': int(self.ai_n_clusters.get() or 10),
            }
        except Exception as e:
            logger.error(f"✗ Ошибка get_ai_settings: {e}")
            import traceback
            traceback.print_exc()
            return {
                'lemmatize': True,
                'max_features': 1000,
                'clustering_mode': 'threshold',
                'threshold': 0.5,
                'n_clusters': 10,
            }
    
    def set_settings(self, settings: Dict):
        """Установить настройки"""
        try:
            self.settings_api_key.set(settings.get('api_key', ''))
            self.settings_folder_id.set(settings.get('folder_id', ''))
            self.settings_depth.set(str(settings.get('depth', 2)))
            self.settings_top_n.set(str(settings.get('top_n', 3)))
            self.settings_num_phrases.set(str(settings.get('num_phrases', 100)))
            self.settings_max_rps.set(str(settings.get('max_rps', 10)))
            self.settings_max_hour.set(str(settings.get('max_hour', 10000)))
            self.settings_max_day.set(str(settings.get('max_day', 1000)))
            
            logger.info("✓ Настройки установлены в UI")
        except Exception as e:
            logger.error(f"✗ Ошибка set_settings: {e}")