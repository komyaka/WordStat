"""
Фильтры для ключевых слов (Т��ОЙНАЯ ПРОВЕРКА)
"""
import re
from typing import List, Optional, Set, Tuple
from enum import Enum

from utils.logger import get_logger
from nlp.normalizer import get_normalizer

logger = get_logger('WordStat.Filters')

class MinusWordMode(Enum):
    """Режимы проверки минус-слов"""
    ANY = "any"  # Любая лемма минус-слова присутствует
    ALL = "all"  # Все леммы минус-фразы присутствуют

class KeywordFilter:
    """Фильтры для ключевых слов"""
    
    def __init__(self):
        self.normalizer = get_normalizer()
        
        # Параметры фильтров
        self.min_count = 1
        self.min_words = 1
        self.max_words = 10
        self.include_regex = None
        self.exclude_regex = None
        self.exclude_substrings: Set[str] = set()
        self.minus_words: List[str] = []
        self.minus_word_mode = MinusWordMode.ANY
        
        logger.info("✓ KeywordFilter инициализирован")
    
    def set_min_count(self, count: int) -> None:
        """Установить минимальный count"""
        if not isinstance(count, int) or count < 1:
            raise ValueError("min_count должен быть int >= 1")
        self.min_count = count
        logger.info(f"✓ min_count установлен: {count}")
    
    def set_word_range(self, min_words: int, max_words: int) -> None:
        """Установить диапазон слов"""
        if not isinstance(min_words, int) or min_words < 1:
            raise ValueError("min_words должен быть int >= 1")
        if not isinstance(max_words, int) or max_words < min_words:
            raise ValueError("max_words должен быть int >= min_words")
        
        self.min_words = min_words
        self.max_words = max_words
        logger.info(f"✓ Word range установлен: {min_words}-{max_words}")
    
    def set_include_regex(self, pattern: str) -> bool:
        """Установить регулярное выражение для включения"""
        if not isinstance(pattern, str):
            raise TypeError("pattern должен быть строкой")
        
        if not pattern:  # ✓ Пустой regex = отключен
            self.include_regex = None
            logger.info("✓ Include regex отключен")
            return True
        
        try:
            self.include_regex = re.compile(pattern, re.IGNORECASE | re.UNICODE)
            logger.info(f"✓ Include regex установлен: {pattern}")
            return True
        except re.error as e:
            logger.error(f"✗ Ошибка include regex: {e}")
            self.include_regex = None
            return False
    
    def set_exclude_regex(self, pattern: str) -> bool:
        """Установить регулярное выражение для исключения"""
        if not isinstance(pattern, str):
            raise TypeError("pattern должен быть строкой")
        
        if not pattern:  # ✓ Пустой regex = отключен
            self.exclude_regex = None
            logger.info("✓ Exclude regex отключен")
            return True
        
        try:
            self.exclude_regex = re.compile(pattern, re.IGNORECASE | re.UNICODE)
            logger.info(f"✓ Exclude regex установлен: {pattern}")
            return True
        except re.error as e:
            logger.error(f"✗ Ошибка exclude regex: {e}")
            self.exclude_regex = None
            return False
    
    def set_exclude_substrings(self, substrings: str) -> None:
        """
        Установить исключающие подстроки (через запятую или новую строку)
        
        ✓ ПРОВЕРКА: Разделение по запятой И новой строке
        """
        if not isinstance(substrings, str):
            raise TypeError("substrings должен быть строкой")
        
        self.exclude_substrings = set()
        
        # ✓ ПРОВЕРКА 1: Разд��ление по запятой и новой строке
        split_chars = substrings.replace('\n', ',').split(',')
        
        for substring in split_chars:
            # ✓ ПРОВЕРКА 2: Trim пробелы и lowercase
            cleaned = substring.strip().lower()
            if cleaned:
                self.exclude_substrings.add(cleaned)
        
        logger.info(f"✓ Исключающие подстроки: {len(self.exclude_substrings)}")
    
    def set_minus_words(self, minus_list: str, mode: str = "any") -> None:
        """
        Установить минус-слова (через запятую или новую строку)
        
        ✓ ПРОВЕРКА: Лемматизация и валидация
        """
        if not isinstance(minus_list, str):
            raise TypeError("minus_list должен быть строкой")
        if mode not in ['any', 'all']:
            raise ValueError("mode должен быть 'any' или 'all'")
        
        self.minus_words = []
        
        # ✓ ПРОВЕРКА 1: Правильное разделение
        split_chars = minus_list.replace('\n', ',').split(',')
        
        for w in split_chars:
            # ✓ ПРОВЕРКА 2: Trim и нормализация
            normalized = self.normalizer.normalize_phrase(w)
            if normalized:
                self.minus_words.append(normalized)
        
        # ✓ ПРОВЕРКА 3: Режим выбран правильно
        self.minus_word_mode = MinusWordMode.ALL if mode == "all" else MinusWordMode.ANY
        logger.info(f"✓ Минус-слова установлены ({len(self.minus_words)} шт, режим={mode})")
    
    def _check_minus_words(self, phrase: str) -> bool:
        """
        Проверить наличие минус-слов (возвращает True если нужно исключить)
        
        ✓ ПРОВЕРКА: Лемматизированные минус-слова
        """
        if not self.minus_words:
            return False
        
        phrase_lemmas = self.normalizer.lemmatize_set(phrase)
        
        if not phrase_lemmas:
            return False
        
        for minus_word in self.minus_words:
            minus_lemmas = self.normalizer.lemmatize_set(minus_word)
            
            if not minus_lemmas:
                continue
            
            if self.minus_word_mode == MinusWordMode.ANY:
                # ✓ ПРОВЕРКА: Любая лемма минус-слова присутствует
                if phrase_lemmas & minus_lemmas:  # Пересечение множеств
                    return True
            
            elif self.minus_word_mode == MinusWordMode.ALL:
                # ✓ ПРОВЕРКА: Все леммы минус-фразы присутствуют
                if minus_lemmas <= phrase_lemmas:  # Подмножество
                    return True
        
        return False
    
    def apply(self, phrase: str, count: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """
        Применить все фильтры
        
        Args:
            phrase: Ключевое слово
            count: Количество (опционально)
        
        Returns:
            (passed, reason_if_rejected)
        """
        # ✓ ПРОВЕРКА 1: Валидация входных данных
        if not isinstance(phrase, str):
            return False, "Фраза не строка"
        
        phrase_normalized = self.normalizer.normalize_phrase(phrase)
        
        if not phrase_normalized:
            return False, "Пустая фраза"
        
        # ✓ ПРОВЕРКА 2: min_count
        if count is not None:
            if not isinstance(count, int) or count < 0:
                return False, "Неверный count"
            if count < self.min_count:
                return False, f"count {count} < min_count {self.min_count}"
        
        # ✓ ПРОВЕРКА 3: Количество слов
        word_count = len(phrase_normalized.split())
        if word_count < self.min_words or word_count > self.max_words:
            return False, f"Слов: {word_count} (требуется {self.min_words}-{self.max_words})"
        
        # ✓ ПРОВЕРКА 4: Include regex (только если установлена)
        if self.include_regex is not None:
            try:
                if not self.include_regex.search(phrase_normalized):
                    return False, "Не соответствует include regex"
            except Exception as e:
                logger.warning(f"Ошибка include regex: {e}")
                return False, "Ошибка в include regex"
        
        # ✓ ПРОВЕРКА 5: Exclude regex (только если установлена)
        if self.exclude_regex is not None:
            try:
                if self.exclude_regex.search(phrase_normalized):
                    return False, "Соответствует exclude regex"
            except Exception as e:
                logger.warning(f"Ошибка exclude regex: {e}")
                return False, "Ошибка в exclude regex"
        
        # ✓ ПРОВЕРКА 6: Исключающие подстроки
        for substring in self.exclude_substrings:
            if substring in phrase_normalized:
                return False, f"Содержит исключаемую подстроку: '{substring}'"
        
        # ✓ ПРОВЕРКА 7: Минус-слова (лемматизир��ванные)
        if self._check_minus_words(phrase_normalized):
            return False, "Содержит минус-слово"
        
        return True, None