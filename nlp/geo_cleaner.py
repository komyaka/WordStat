"""
Очистка геоданных из ключевых слов
"""
from enum import Enum
from typing import Tuple, List, Optional
import re

from utils.logger import get_logger
from utils.constants import GEO_KEYWORDS

logger = get_logger('WordStat.NLP.GeoCleaner')


class GeoMode(Enum):
    """Режимы обработки геоданных"""
    OFF = "off"           # Не обрабатывать
    REMOVE = "remove"     # Удалить гео-слова
    EXTRACT = "extract"   # Извлечь гео-слова


class GeoCleaner:
    """Очистка геоданных"""
    
    def __init__(self):
        """Инициализация"""
        try:
            self.geo_keywords = GEO_KEYWORDS
            logger.info(f"✓ GeoCleaner инициализирован ({len(self.geo_keywords)} гео-слов)")
        
        except Exception as e:
            logger.error(f"✗ Ошибка инициализации GeoCleaner: {e}")
            self.geo_keywords = set()
    
    def process(self, phrase: str, mode: GeoMode = GeoMode.OFF) -> Tuple[Optional[str], List[str]]:
        """
        Обработать фразу
        
        Returns:
            (processed_phrase, geo_tokens)
        """
        try:
            if not isinstance(phrase, str):
                return None, []
            
            if mode == GeoMode.OFF:
                return phrase, []
            
            phrase_lower = phrase.lower()
            found_geo = []
            
            # Найти все гео-слова
            for geo_word in self.geo_keywords:
                if geo_word in phrase_lower:
                    found_geo.append(geo_word)
            
            if mode == GeoMode.REMOVE:
                # Удалить гео-слова
                processed = phrase
                for geo_word in found_geo:
                    processed = re.sub(rf'\b{re.escape(geo_word)}\b', '', processed, flags=re.IGNORECASE)
                
                processed = re.sub(r'\s+', ' ', processed).strip()
                
                if not processed:
                    logger.debug(f"⊘ Фраза полностью удалена (только гео): {phrase}")
                    return None, found_geo
                
                return processed, found_geo
            
            elif mode == GeoMode.EXTRACT:
                # Только гео-слова
                if not found_geo:
                    logger.debug(f"⊘ Гео-слова не найдены: {phrase}")
                    return None, []
                
                return phrase, found_geo
            
            return phrase, found_geo
        
        except Exception as e:
            logger.error(f"✗ Ошибка process: {e}")
            return phrase, []
    
    def has_geo(self, phrase: str) -> bool:
        """Проверить наличие гео-слов"""
        try:
            phrase_lower = phrase.lower()
            for geo_word in self.geo_keywords:
                if geo_word in phrase_lower:
                    return True
            return False
        
        except Exception as e:
            logger.error(f"✗ Ошибка has_geo: {e}")
            return False