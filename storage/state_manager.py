"""
Управление состоянием парсинга и сохранение результатов
"""
import json
import os
import shutil
import threading
from typing import Optional, Dict, List
from datetime import datetime

from utils.logger import get_logger
from storage.models import SessionState, KeywordData

logger = get_logger('WordStat.State')


class StateManager:
    """Менеджер состояния"""
    
    def __init__(self, state_file: str = "output.state.json", tsv_file: str = "output.tsv"):
        """
        Args:
            state_file: Путь к файлу состояния
            tsv_file: Путь к файлу TSV
        """
        self.state_file = state_file
        self.tsv_file = tsv_file
        self.lock = threading.RLock()
        
        logger.info(f"✓ StateManager инициализирован (state={state_file}, tsv={tsv_file})")
    
    def save_state(self, state: SessionState) -> None:
        """Сохранить состояние сессии"""
        try:
            if not state or not state.keywords:
                logger.warning("⚠ Пустое состояние, пропускаю")
                return
            
            logger.info(f"💾 Сохраняю state: {self.state_file} ({len(state.keywords)} ключей)")
            
            with self.lock:
                state_dict = state.to_dict()
                
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    json.dump(state_dict, f, ensure_ascii=False, indent=2)
            
            # ✅ Проверить
            if os.path.exists(self.state_file):
                file_size = os.path.getsize(self.state_file)
                logger.info(f"✓ State сохранён: {self.state_file} ({file_size} байт)")
            else:
                logger.error(f"✗ State файл не создан: {self.state_file}")
            
            # ✅ СОХРАНИТЬ ТАКЖЕ TSV
            self.save_tsv(state.keywords)
        
        except Exception as e:
            logger.error(f"✗ Ошибка сохранения state: {e}")
            import traceback
            traceback.print_exc()
    
    def load_state(self) -> Optional[SessionState]:
        """Загрузить состояние сессии"""
        try:
            if not os.path.exists(self.state_file):
                logger.warning(f"⚠ State файл не найден: {self.state_file}")
                return None
            
            logger.info(f"📖 Загружаю state: {self.state_file}")
            
            with self.lock:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state_dict = json.load(f)
            
            state = SessionState.from_dict(state_dict)
            logger.info(f"✓ State загружен: {len(state.keywords)} ключей")
            return state
        
        except Exception as e:
            logger.error(f"✗ Ошибка загрузки state: {e}")
            return None
    
    def save_tsv(self, keywords: Dict[str, KeywordData]) -> None:
        """Сохранить результаты в TSV"""
        try:
            if not keywords:
                logger.warning("⚠ Нет ключевых слов для сохранения в TSV")
                return
            
            logger.info(f"💾 Сохраняю TSV: {self.tsv_file} ({len(keywords)} ключей)")
            
            with self.lock:
                # ✅ ОТКРЫТЬ ФАЙЛ И ОЧИСТИТЬ
                with open(self.tsv_file, 'w', encoding='utf-8', newline='') as f:
                    # ✅ ЗАГОЛОВОК
                    header = "Фраза\tCount\tSeed\tDepth\tSource\tTimestamp\n"
                    f.write(header)
                    logger.debug(f"📝 Написан заголовок TSV")
                    
                    # ✅ ОТСОРТИРОВАТЬ ПО COUNT
                    sorted_kw = sorted(keywords.values(), key=lambda k: k.count, reverse=True)
                    logger.debug(f"📊 Ключей отсортировано: {len(sorted_kw)}")
                    
                    # ✅ НАПИСАТЬ СТРОКИ
                    lines_written = 0
                    for idx, kwd in enumerate(sorted_kw):
                        try:
                            source = kwd.source or kwd.origin or "API"
                            line = f"{kwd.phrase}\t{kwd.count}\t{kwd.seed}\t{kwd.depth}\t{source}\t{kwd.timestamp}\n"
                            f.write(line)
                            lines_written += 1
                        except Exception as e:
                            logger.warning(f"⚠ Ошибка записи строки {idx}: {e}")
                    
                    logger.info(f"✓ Записано строк: {lines_written}")
            
            # ✅ ПРОВЕРИТЬ ЧТО ФАЙЛ СОЗДАН И НЕ ПУСТ
            if os.path.exists(self.tsv_file):
                file_size = os.path.getsize(self.tsv_file)
                logger.info(f"✓ TSV сохранён: {self.tsv_file} ({file_size} байт)")
                
                # ✅ ПРОВЕРИТЬ СОДЕРЖИМОЕ
                try:
                    with open(self.tsv_file, 'r', encoding='utf-8') as f:
                        file_lines = len(f.readlines())
                    logger.info(f"✓ TSV содержит {file_lines} строк (включая заголовок)")
                    
                    if file_lines <= 1:
                        logger.warning(f"⚠ ВНИМАНИЕ: TSV содержит только заголовок!")
                except Exception as e:
                    logger.warning(f"⚠ Ошибка проверки содержимого TSV: {e}")
            else:
                logger.error(f"✗ TSV файл НЕ создан: {self.tsv_file}")
        
        except Exception as e:
            logger.error(f"✗ Ошибка сохранения TSV: {e}")
            import traceback
            traceback.print_exc()
    
    def clear_tsv(self):
        """Очистить TSV"""
        try:
            if os.path.exists(self.tsv_file):
                os.remove(self.tsv_file)
                logger.info(f"🧹 TSV очищен: {self.tsv_file}")
        except Exception as e:
            logger.error(f"✗ Ошибка очистки TSV: {e}")
    
    def clear_state(self):
        """Очистить STATE"""
        try:
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
                logger.info(f"🧹 STATE очищен: {self.state_file}")
        except Exception as e:
            logger.error(f"✗ Ошибка очистки STATE: {e}")