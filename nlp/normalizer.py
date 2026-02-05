"""
Нормализация и лемматизация текста
"""
import threading
from typing import List, Set, Optional
import re

from utils.logger import get_logger
from utils.constants import RUSSIAN_STOP_WORDS, MORPH_ANALYZER_LANG

logger = get_logger('WordStat.NLP.Normalizer')

try:
    import pymorphy3
    PYMORPHY_AVAILABLE = True
except ImportError:
    logger.warning("⚠ pymorphy3 не установлен, лемматизация отключена")
    PYMORPHY_AVAILABLE = False


class Normalizer:
    """Нормализация и лемматизация текста"""
    
    def __init__(self):
        """Инициализация"""
        try:
            if PYMORPHY_AVAILABLE:
                self.morph = pymorphy3.MorphAnalyzer()
            else:
                self.morph = None
            
            self.morph_lock = threading.RLock()
            
            logger.info(f"✓ Normalizer инициализирован (pymorphy3: {PYMORPHY_AVAILABLE})")
        
        except Exception as e:
            logger.error(f"✗ Ошибка инициализации Normalizer: {e}")
            self.morph = None
    
    def normalize_phrase(self, phrase: str) -> str:
        """
        Нормализовать фразу
        - Привести к нижнему регистру
        - Убрать лишние пробелы
        - Убрать спецсимволы
        """
        try:
            if not isinstance(phrase, str):
                return ""
            
            # Нижний регистр
            phrase = phrase.lower().strip()
            
            # Удалить лишние пробелы
            phrase = re.sub(r'\s+', ' ', phrase)
            
            # Оставить только буквы, цифры и пробелы (кириллица + латиница)
            phrase = re.sub(r'[^\w\s\-а-яё]', '', phrase, flags=re.UNICODE)
            
            # Удалить лишние пробелы снова
            phrase = phrase.strip()
            
            return phrase
        
        except Exception as e:
            logger.error(f"✗ Ошибка normalize_phrase: {e}")
            return ""
    
    def lemmatize_phrase(self, phrase: str) -> List[str]:
        """
        Лемматизировать фразу (привести к начальной форме)
        Возвращает список лемм
        """
        try:
            if not self.morph:
                # Если pymorphy3 не доступен, просто разбить на слова
                return phrase.split()
            
            normalized = self.normalize_phrase(phrase)
            if not normalized:
                return []
            
            words = normalized.split()
            lemmas = []
            
            with self.morph_lock:
                for word in words:
                    try:
                        parsed = self.morph.parse(word)[0]
                        lemma = parsed.normal_form
                        lemmas.append(lemma)
                    except Exception as e:
                        logger.debug(f"⚠ Ошибка лемматизации '{word}': {e}")
                        lemmas.append(word)
            
            return lemmas
        
        except Exception as e:
            logger.error(f"✗ Ошибка lemmatize_phrase: {e}")
            return phrase.split()
    
    def lemmatize_set(self, phrase: str) -> Set[str]:
        """
        Лемматизировать фразу и вернуть множество лемм.
        Используется для сравнения наличия минус-слов.
        
        Args:
            phrase: Фраза для лемматизации
            
        Returns:
            Множество лемм (без стоп-слов)
        """
        try:
            lemmas = self.lemmatize_phrase(phrase)
            # Исключаем стоп-слова и возвращаем как множество
            result = set()
            for lemma in lemmas:
                lower_lemma = lemma.lower()
                if lower_lemma not in RUSSIAN_STOP_WORDS:
                    result.add(lower_lemma)
            return result
        except Exception as e:
            logger.error(f"✗ Ошибка lemmatize_set: {e}")
            normalized = self.normalize_phrase(phrase)
            return set(normalized.split()) if normalized else set()
    
    def remove_stop_words(self, phrase: str) -> str:
        """
        Удалить стоп-слова из фразы
        """
        try:
            normalized = self.normalize_phrase(phrase)
            if not normalized:
                return ""
            
            words = normalized.split()
            filtered = [w for w in words if w.lower() not in RUSSIAN_STOP_WORDS]
            
            return ' '.join(filtered)
        
        except Exception as e:
            logger.error(f"✗ Ошибка remove_stop_words: {e}")
            return phrase
    
    def get_word_count(self, phrase: str) -> int:
        """
        Получить количество слов в фразе
        """
        try:
            normalized = self.normalize_phrase(phrase)
            if not normalized:
                return 0
            
            words = normalized.split()
            return len(words)
        
        except Exception as e:
            logger.error(f"✗ Ошибка get_word_count: {e}")
            return 0
    
    def lemmatize_set(self, phrase: str) -> Set[str]:
        """
        Лемматизировать фразу и вернуть множество лемм.
        Используется для проверки минус-слов.
        
        Returns:
            Множество лемм из фразы
        """
        try:
            lemmas = self.lemmatize_phrase(phrase)
            return set(lemmas)
        
        except Exception as e:
            logger.error(f"✗ Ошибка lemmatize_set: {e}")
            return set()
    
    @staticmethod
    def is_valid_keyword(phrase: str) -> bool:
        """
        Проверить что фраза валидное ключевое слово
        """
        try:
            if not isinstance(phrase, str):
                return False
            
            phrase = phrase.strip()
            
            if not phrase:
                return False
            
            # Минимум 1 символ
            if len(phrase) < 1:
                return False
            
            # Максимум 100 символов
            if len(phrase) > 100:
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"✗ Ошибка is_valid_keyword: {e}")
            return False


# ✅ ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР НОРМАЛИЗАТОРА
_normalizer_instance: Optional[Normalizer] = None
_normalizer_lock = threading.RLock()


def get_normalizer() -> Normalizer:
    """Получить глобальный экземпляр нормализатора"""
    global _normalizer_instance
    
    if _normalizer_instance is None:
        with _normalizer_lock:
            if _normalizer_instance is None:
                try:
                    _normalizer_instance = Normalizer()
                except Exception as e:
                    logger.error(f"✗ Ошибка создания Normalizer: {e}")
                    raise
    
    return _normalizer_instance