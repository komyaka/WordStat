"""
Темы оформления и конфигурация UI
"""
import customtkinter as ctk


class AppTheme:
    """Темы приложения"""
    
    LIGHT_THEME = {
        'bg_color': '#FFFFFF',
        'fg_color': '#000000',
        'button_color': '#4A90E2',
        'button_hover': '#357ABD',
        'entry_color': '#F5F5F5',
        'text_color': '#333333',
    }
    
    DARK_THEME = {
        'bg_color': '#2B2B2B',
        'fg_color': '#FFFFFF',
        'button_color': '#4A90E2',
        'button_hover': '#357ABD',
        'entry_color': '#3A3A3A',
        'text_color': '#E0E0E0',
    }
    
    @staticmethod
    def get_theme(name: str = 'dark') -> dict:
        """Получить тему"""
        if name.lower() == 'light':
            return AppTheme.LIGHT_THEME
        else:
            return AppTheme.DARK_THEME


class UIConfig:
    """Конфигурация UI"""
    
    # Размеры окна
    WINDOW_WIDTH = 1600
    WINDOW_HEIGHT = 1000
    
    # Отступы
    PADDING_SMALL = 5
    PADDING_NORMAL = 10
    PADDING_LARGE = 20
    
    # ✅ ШРИФТЫ - УВЕЛИЧЕНЫ ДЛЯ ВИДИМОСТИ
    FONT_SMALL = ('Segoe UI', 11)
    FONT_NORMAL = ('Segoe UI', 12)
    FONT_MONO = ('Courier New', 11)
    FONT_HEADER = ('Segoe UI', 14, 'bold')
    FONT_TITLE = ('Segoe UI', 18, 'bold')
    
    # ✅ ЦВЕТА - ЯРКИЕ И КОНТРАСТНЫЕ
    COLOR_SUCCESS = '#00CC44'
    COLOR_ERROR = '#FF4444'
    COLOR_WARNING = '#FFAA00'
    COLOR_INFO = '#44AAFF'
    COLOR_DISABLED = '#666666'
    
    # ✅ ЦВЕТА ФОНА И ТЕКСТА
    BG_PRIMARY = '#1E1E1E'
    BG_SECONDARY = '#2D2D2D'
    BG_TERTIARY = '#3A3A3A'
    TEXT_PRIMARY = '#FFFFFF'
    TEXT_SECONDARY = '#CCCCCC'
    TEXT_TERTIARY = '#999999'
    
    # Размеры элементов
    BUTTON_WIDTH = 150
    BUTTON_HEIGHT = 40
    ENTRY_HEIGHT = 35
    
    # Таблица
    TABLE_HEIGHT = 200
    TABLE_WIDTH = 600
    
    # Интервалы
    UPDATE_INTERVAL_MS = 100
    LOG_MAX_ROWS = 100