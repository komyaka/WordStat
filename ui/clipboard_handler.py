"""
Обработка Clipboard (Ctrl+C/V/X/A + контекстное меню)
"""
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from utils.logger import get_logger

logger = get_logger('WordStat.Clipboard')


class ClipboardHandler:
    """Обработчик буфера обмена"""
    
    def __init__(self, widget):
        """Инициализация"""
        try:
            self.widget = widget
            self.setup_context_menu()
            self.setup_keybindings()
        except Exception as e:
            logger.error(f"✗ Ошибка инициализации ClipboardHandler: {e}")
    
    def setup_context_menu(self):
        """Установить контекстное меню"""
        try:
            self.context_menu = tk.Menu(self.widget, tearoff=0)
            self.context_menu.add_command(label="Копировать", command=self._on_copy)
            self.context_menu.add_command(label="Вырезать", command=self._on_cut)
            self.context_menu.add_command(label="Вставить", command=self._on_paste)
            self.context_menu.add_separator()
            self.context_menu.add_command(label="Выделить всё", command=self._on_select_all)
            
            self.widget.bind("<Button-3>", self._show_context_menu)
        except Exception as e:
            logger.error(f"✗ Ошибка setup_context_menu: {e}")
    
    def setup_keybindings(self):
        """Установить горячие клавиши"""
        try:
            self.widget.bind("<Control-c>", lambda e: self._on_copy())
            self.widget.bind("<Control-x>", lambda e: self._on_cut())
            self.widget.bind("<Control-v>", lambda e: self._on_paste())
            self.widget.bind("<Control-a>", lambda e: self._on_select_all())
        except Exception as e:
            logger.error(f"✗ Ошибка setup_keybindings: {e}")
    
    def _show_context_menu(self, event):
        """Показать контекстное меню"""
        try:
            self.context_menu.post(event.x_root, event.y_root)
        except Exception as e:
            logger.debug(f"⚠ Ошибка меню: {e}")
    
    def _on_copy(self):
        """Копировать"""
        try:
            self._copy()
        except Exception as e:
            logger.debug(f"⚠ Ошибка копирования: {e}")
    
    def _on_paste(self):
        """Вставить"""
        try:
            self._paste()
        except Exception as e:
            logger.debug(f"⚠ Ошибка вставки: {e}")
    
    def _on_cut(self):
        """Вырезать"""
        try:
            self._cut()
        except Exception as e:
            logger.debug(f"⚠ Ошибка вырезания: {e}")
    
    def _on_select_all(self):
        """Выделить всё"""
        try:
            self._select_all()
        except Exception as e:
            logger.debug(f"⚠ Ошибка выделения: {e}")
    
    def _copy(self):
        """Копировать текст"""
        try:
            if hasattr(self.widget, 'selection_get'):
                text = self.widget.selection_get()
                self.widget.clipboard_clear()
                self.widget.clipboard_append(text)
                self.widget.update()
                logger.debug(f"✓ Скопировано: {len(text)} символов")
        except Exception as e:
            logger.debug(f"⊘ Копировать: {e}")
    
    def _cut(self):
        """Вырезать текст"""
        try:
            self._copy()
            if hasattr(self.widget, 'delete'):
                self.widget.delete("sel.first", "sel.last")
                logger.debug(f"✓ Вырезано")
        except Exception as e:
            logger.debug(f"⊘ Вырезать: {e}")
    
    def _paste(self):
        """Вставить текст"""
        try:
            if hasattr(self.widget, 'insert'):
                text = self.widget.clipboard_get()
                self.widget.insert("insert", text)
                logger.debug(f"✓ Вставлено: {len(text)} символов")
        except Exception as e:
            logger.debug(f"⊘ Вставить: {e}")
    
    def _select_all(self):
        """Выделить весь текст"""
        try:
            if hasattr(self.widget, 'tag_add'):
                self.widget.tag_add("sel", "1.0", "end")
            elif hasattr(self.widget, 'select_range'):
                self.widget.select_range(0, "end")
            logger.debug(f"✓ Выделено всё")
        except Exception as e:
            logger.debug(f"⊘ Выделение: {e}")