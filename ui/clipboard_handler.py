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
            self.widget.bind("<Control-c>", self._on_copy_event)
            self.widget.bind("<Control-x>", self._on_cut_event)
            self.widget.bind("<Control-v>", self._on_paste_event)
            self.widget.bind("<Control-a>", self._on_select_all_event)
            # Add uppercase bindings for different keyboard states
            self.widget.bind("<Control-C>", self._on_copy_event)
            self.widget.bind("<Control-X>", self._on_cut_event)
            self.widget.bind("<Control-V>", self._on_paste_event)
            self.widget.bind("<Control-A>", self._on_select_all_event)
        except Exception as e:
            logger.error(f"✗ Ошибка setup_keybindings: {e}")
    
    def _is_entry_widget(self) -> bool:
        """Проверить, является ли виджет CTkEntry (имеет _entry, но не _textbox)"""
        return hasattr(self.widget, '_entry') and not hasattr(self.widget, '_textbox')

    def _get_inner_widget(self):
        """Получить внутренний tk-виджет (tk.Entry или tk.Text)"""
        if self._is_entry_widget():
            return self.widget._entry
        return self.widget._textbox if hasattr(self.widget, '_textbox') else self.widget


        """Показать контекстное меню"""
        try:
            self.context_menu.post(event.x_root, event.y_root)
        except Exception as e:
            logger.debug(f"⚠ Ошибка меню: {e}")
    
    def _on_copy_event(self, event=None):
        """Обработчик события копирования"""
        try:
            self._copy()
        except Exception as e:
            logger.debug(f"⚠ Ошибка копирования: {e}")
        return "break"
    
    def _on_paste_event(self, event=None):
        """Обработчик события вставки"""
        try:
            self._paste()
        except Exception as e:
            logger.debug(f"⚠ Ошибка вставки: {e}")
        return "break"
    
    def _on_cut_event(self, event=None):
        """Обработчик события вырезания"""
        try:
            self._cut()
        except Exception as e:
            logger.debug(f"⚠ Ошибка вырезания: {e}")
        return "break"
    
    def _on_select_all_event(self, event=None):
        """Обработчик события выделения всего"""
        try:
            self._select_all()
        except Exception as e:
            logger.debug(f"⚠ Ошибка выделения: {e}")
        return "break"
    
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
            text = None

            if self._is_entry_widget():
                # CTkEntry: использовать внутренний tk.Entry
                entry = self.widget._entry
                try:
                    if entry.selection_present():
                        text = entry.selection_get()
                except (tk.TclError, AttributeError):
                    pass
            else:
                # CTkTextbox: использовать внутренний tk.Text
                textbox = self._get_inner_widget()
                try:
                    sel_ranges = textbox.tag_ranges("sel")
                    if sel_ranges:
                        text = textbox.get(sel_ranges[0], sel_ranges[1])
                except (tk.TclError, AttributeError):
                    pass

                # Fallback через selection_get
                if text is None:
                    try:
                        text = self.widget.selection_get()
                    except (tk.TclError, AttributeError):
                        pass

            if text:
                self.widget.clipboard_clear()
                self.widget.clipboard_append(text)
                self.widget.update()
                logger.debug(f"✓ Скопировано: {len(text)} символов")
        except Exception as e:
            logger.debug(f"⊘ Копировать: {e}")
    
    def _cut(self):
        """Вырезать текст"""
        try:
            # Сначала копировать
            self._copy()

            if self._is_entry_widget():
                # CTkEntry: удалить выделение через внутренний tk.Entry
                entry = self.widget._entry
                try:
                    if entry.selection_present():
                        entry.delete("sel.first", "sel.last")
                    logger.debug("✓ Вырезано (Entry)")
                except (tk.TclError, AttributeError):
                    pass
            else:
                # CTkTextbox: удалить через внутренний tk.Text виджет
                textbox = self._get_inner_widget()
                try:
                    try:
                        textbox.delete("sel.first", "sel.last")
                    except (tk.TclError, AttributeError):
                        sel_ranges = textbox.tag_ranges("sel")
                        if sel_ranges:
                            textbox.delete(sel_ranges[0], sel_ranges[1])
                    logger.debug("✓ Вырезано (Textbox)")
                except Exception as e:
                    logger.debug(f"⊘ Удаление после вырезания: {e}")
        except Exception as e:
            logger.debug(f"⊘ Вырезать: {e}")
    
    def _paste(self):
        """Вставить текст"""
        try:
            text = self.widget.clipboard_get()

            if self._is_entry_widget():
                # CTkEntry: использовать внутренний tk.Entry
                entry = self.widget._entry
                try:
                    if entry.selection_present():
                        entry.delete("sel.first", "sel.last")
                except (tk.TclError, AttributeError):
                    pass
                entry.insert(tk.INSERT, text)
                logger.debug(f"✓ Вставлено (Entry): {len(text)} символов")
            else:
                # CTkTextbox: использовать внутренний tk.Text виджет
                textbox = self._get_inner_widget()
                try:
                    sel_ranges = textbox.tag_ranges("sel") if hasattr(textbox, 'tag_ranges') else None
                    if sel_ranges:
                        textbox.delete(sel_ranges[0], sel_ranges[1])
                except (tk.TclError, AttributeError):
                    pass
                if hasattr(textbox, 'insert'):
                    textbox.insert("insert", text)
                logger.debug(f"✓ Вставлено (Textbox): {len(text)} символов")
        except Exception as e:
            logger.debug(f"⊘ Вставить: {e}")
    
    def _select_all(self):
        """Выделить весь текст"""
        try:
            if self._is_entry_widget():
                # CTkEntry: использовать внутренний tk.Entry
                entry = self.widget._entry
                entry.select_range(0, tk.END)
                entry.icursor(tk.END)
            else:
                # CTkTextbox: использовать внутренний tk.Text виджет
                textbox = self._get_inner_widget()
                if hasattr(textbox, 'tag_add'):
                    textbox.tag_add("sel", "1.0", "end-1c")
                    textbox.mark_set("insert", "1.0")
                    textbox.see("insert")

            try:
                self.widget.focus_set()
            except (tk.TclError, AttributeError):
                pass

            logger.debug("✓ Выделено всё")
        except Exception as e:
            logger.debug(f"⊘ Выделение: {e}")