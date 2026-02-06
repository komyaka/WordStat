"""
Кастомные виджеты для приложения
"""
import customtkinter as ctk
from typing import Optional, Callable
import tkinter as tk
from tkinter import ttk

from .styles import UIConfig
from .clipboard_handler import ClipboardHandler
from utils.logger import get_logger

logger = get_logger('WordStat.UI.Widgets')

# Delay for counter update after paste (allows paste operation to complete)
PASTE_COUNTER_UPDATE_DELAY_MS = 100


class LabeledEntry(ctk.CTkFrame):
    """Entry с меткой слева"""
    
    def __init__(self, parent, label_text: str, placeholder: str = "", **kwargs):
        super().__init__(parent, **kwargs)
        
        try:
            self.label = ctk.CTkLabel(
                self,
                text=label_text,
                font=UIConfig.FONT_NORMAL,
                width=150
            )
            self.label.pack(side='left', padx=(0, UIConfig.PADDING_SMALL))
            
            self.entry = ctk.CTkEntry(
                self,
                placeholder_text=placeholder,
                font=UIConfig.FONT_NORMAL
            )
            self.entry.pack(side='left', fill='x', expand=True)
            
            ClipboardHandler(self.entry)
        except Exception as e:
            logger.error(f"✗ Ошибка инициализации LabeledEntry: {e}")
    
    def get(self) -> str:
        """Получить значение"""
        try:
            return self.entry.get()
        except Exception as e:
            logger.error(f"✗ Ошибка get(): {e}")
            return ""
    
    def set(self, value: str):
        """Установить значение"""
        try:
            self.entry.delete(0, 'end')
            self.entry.insert(0, value)
        except Exception as e:
            logger.error(f"✗ Ошибка set(): {e}")


class LabeledTextbox(ctk.CTkFrame):
    """Textbox с меткой и счётчиком строк"""
    
    def __init__(self, parent, label_text: str, height: int = 150, **kwargs):
        super().__init__(parent, **kwargs)
        
        try:
            self.label = ctk.CTkLabel(
                self,
                text=label_text,
                font=UIConfig.FONT_HEADER
            )
            self.label.pack(anchor='w', pady=(0, UIConfig.PADDING_SMALL))
            
            text_frame = ctk.CTkFrame(self)
            text_frame.pack(fill='both', expand=True)
            
            self.textbox = ctk.CTkTextbox(
                text_frame,
                font=UIConfig.FONT_MONO,
                height=height
            )
            self.textbox.pack(side='left', fill='both', expand=True)
            
            ClipboardHandler(self.textbox)
            
            self.counter = ctk.CTkLabel(
                self,
                text="Строк: 0",
                font=UIConfig.FONT_SMALL,
                text_color='gray'
            )
            self.counter.pack(anchor='e', pady=(UIConfig.PADDING_SMALL, 0))
            
            self.textbox.bind('<KeyRelease>', self._on_text_change)
            # Update counter after paste operations
            self.textbox.bind('<Control-v>', lambda e: self.after(PASTE_COUNTER_UPDATE_DELAY_MS, self._update_counter))
            self.textbox.bind('<Control-V>', lambda e: self.after(PASTE_COUNTER_UPDATE_DELAY_MS, self._update_counter))
        
        except Exception as e:
            logger.error(f"✗ Ошибка инициализации LabeledTextbox: {e}")
    
    def _on_text_change(self, event=None):
        """Обновить счётчик строк"""
        self._update_counter()
    
    def _update_counter(self):
        """Обновить счётчик"""
        try:
            content = self.textbox.get("1.0", "end-1c")
            lines = content.count('\n') + 1 if content else 1
            self.counter.configure(text=f"Строк: {lines}")
        except Exception as e:
            logger.debug(f"⚠ Ошибка _update_counter: {e}")
    
    def get(self) -> str:
        """Получить значение"""
        try:
            return self.textbox.get("1.0", "end-1c")
        except Exception as e:
            logger.error(f"✗ Ошибка get(): {e}")
            return ""
    
    def set(self, value: str):
        """Установить значение"""
        try:
            self.textbox.delete("1.0", "end")
            self.textbox.insert("1.0", value)
            self._update_counter()
        except Exception as e:
            logger.error(f"✗ Ошибка set(): {e}")


class StatCard(ctk.CTkFrame):
    """Карточка со статистикой"""
    
    def __init__(self, parent, title: str, value: str = "0", **kwargs):
        super().__init__(parent, **kwargs)
        
        try:
            self.title_label = ctk.CTkLabel(
                self,
                text=title,
                font=UIConfig.FONT_SMALL,
                text_color='gray'
            )
            self.title_label.pack(anchor='w', padx=UIConfig.PADDING_SMALL, pady=(UIConfig.PADDING_SMALL, 0))
            
            self.value_label = ctk.CTkLabel(
                self,
                text=value,
                font=UIConfig.FONT_HEADER
            )
            self.value_label.pack(anchor='w', padx=UIConfig.PADDING_SMALL, pady=(0, UIConfig.PADDING_SMALL))
        
        except Exception as e:
            logger.error(f"✗ Ошибка инициализации StatCard: {e}")
    
    def set_value(self, value: str):
        """Об��овить значение"""
        try:
            self.value_label.configure(text=value)
        except Exception as e:
            logger.error(f"✗ Ошибка set_value(): {e}")


class LogTable(ctk.CTkFrame):
    """Таблица логирования"""
    
    def __init__(self, parent, max_rows: int = 100, **kwargs):
        super().__init__(parent, **kwargs)
        
        try:
            self.max_rows = max_rows
            self.rows = []
            
            columns = ('Фраза', 'Count', 'Источник', 'Depth', 'Seed', 'Timestamp')
            
            self.tree = ttk.Treeview(
                self,
                columns=columns,
                height=15,
                show='tree headings'
            )
            
            self.tree.column('#0', width=0, stretch=tk.NO)
            self.tree.column('Фраза', anchor=tk.W, width=250)
            self.tree.column('Count', anchor=tk.CENTER, width=80)
            self.tree.column('Источник', anchor=tk.CENTER, width=80)
            self.tree.column('Depth', anchor=tk.CENTER, width=60)
            self.tree.column('Seed', anchor=tk.W, width=150)
            self.tree.column('Timestamp', anchor=tk.CENTER, width=150)
            
            for col in columns:
                self.tree.heading(col, text=col)
            
            scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
            self.tree.configure(yscroll=scrollbar.set)
            
            self.tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')
        
        except Exception as e:
            logger.error(f"✗ Ошибка инициализации LogTable: {e}")
    
    def add_row(self, phrase: str, count: str, source: str, depth: str, seed: str, timestamp: str):
        """Добавить строку"""
        try:
            if len(self.rows) >= self.max_rows:
                old_id = self.rows.pop(0)
                self.tree.delete(old_id)
            
            row_id = self.tree.insert('', 'end', values=(phrase, count, source, depth, seed, timestamp))
            self.rows.append(row_id)
            
            self.tree.see(row_id)
        
        except Exception as e:
            logger.debug(f"⚠ Ошибка add_row: {e}")
    
    def clear(self):
        """Очистить таблицу"""
        try:
            for row_id in self.rows:
                self.tree.delete(row_id)
            self.rows.clear()
        except Exception as e:
            logger.error(f"✗ Ошибка clear(): {e}")