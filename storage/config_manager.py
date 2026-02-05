"""
Управление config.json и конфигурацией
"""
import json
import os
import shutil
from typing import Dict, Any, Optional

from utils.logger import get_logger

logger = get_logger('WordStat.Config')

class ConfigManager:
    """Менеджер конфигурации"""
    
    DEFAULT_CONFIG = {
        'api': {
            'key': '',
            'folder_id': '',
            'endpoint': 'wordstat',
            'timeout': 15,
            'retries': 3,
        },
        'parsing': {
            'depth': 2,
            'top_n': 3,
            'num_phrases': 100,
            'regions': None,
            'device': 'all',
            'workers': 3,
        },
        'quotas': {
            'max_rps': 10,
            'max_per_hour': 10000,
            'max_per_day': 100000,
        },
        'filters': {
            'min_count': 10,
            'min_words': 1,
            'max_words': 10,
            'include_regex': '',
            'exclude_regex': '',
            'exclude_substrings': '',
            'minus_words': '',
            'minus_word_mode': 'any',
        },
        'geo': {
            'mode': 'off',
            'custom_path': 'geo_data/geo_custom.txt',
        },
        'ai': {
            'lemmatize': True,
            'threshold': 0.5,
            'n_clusters': 10,
            'max_features': 1000,
            'ngram_range': [1, 2],
            'embedding_model': 'multilingual',
            'use_semantic': True,
        },
        'ui': {
            'theme': 'dark',
            'autosave_interval': 5,
        },
        'cache': {
            'enabled': True,
            'mode': 'on',
            'ttl_days': 7,
        },
    }
    
    def __init__(self, config_path: str = 'config.json'):
        """
        Args:
            config_path: Путь к config.json
        """
        if not isinstance(config_path, str) or not config_path:
            raise ValueError("config_path должен быть непустой строкой")
        
        self.config_path = config_path
        self.config = self.load()
        
        logger.info(f"✓ ConfigManager инициализирован ({config_path})")
    
    def load(self) -> Dict:
        """
        Загрузить конфиг
        """
        try:
            if not os.path.exists(self.config_path):
                logger.info(f"⊘ Конфиг не найден, используются дефолтные значения")
                return self._get_default_config_copy()
            
            if not os.path.isfile(self.config_path):
                logger.warning(f"⚠ config_path не файл")
                return self._get_default_config_copy()
            
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except json.JSONDecodeError as e:
                logger.warning(f"⚠ Ошибка парсинга конфига: {e}, используются дефолтные")
                return self._get_default_config_copy()
            except IOError as e:
                logger.warning(f"⚠ Ошибка чтения конфига: {e}, используются дефолтные")
                return self._get_default_config_copy()
            
            if not isinstance(config, dict):
                logger.warning(f"⚠ Конфиг не dict, используются дефолтные")
                return self._get_default_config_copy()
            
            merged = self._get_default_config_copy()
            self._deep_merge(merged, config)
            
            logger.info(f"✓ Конфиг загружен: {self.config_path}")
            return merged
        
        except Exception as e:
            logger.error(f"✗ Критическая ошибка загрузки конфига: {e}")
            return self._get_default_config_copy()
    
    def _get_default_config_copy(self) -> Dict:
        """Получить копию дефолтного конфига"""
        import copy
        return copy.deepcopy(self.DEFAULT_CONFIG)
    
    def save(self) -> bool:
        """
        Сохранить конфиг
        """
        try:
            if not isinstance(self.config, dict):
                logger.error(f"✗ config не dict, не могу сохранить")
                return False
            
            try:
                json_str = json.dumps(self.config, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"✗ Ошибка сериализации конфига: {e}")
                return False
            
            if os.path.exists(self.config_path):
                backup_path = f"{self.config_path}.backup"
                try:
                    shutil.copy2(self.config_path, backup_path)
                    logger.debug(f"✓ Backup создан: {backup_path}")
                except Exception as e:
                    logger.warning(f"⚠ Ошибка создания backup: {e}")
            
            tmp_path = f"{self.config_path}.tmp"
            
            try:
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    f.write(json_str)
            except IOError as e:
                logger.error(f"✗ Ошибка записи tmp конфига: {e}")
                return False
            
            try:
                os.replace(tmp_path, self.config_path)
            except OSError as e:
                logger.error(f"✗ Ошибка замены конфига: {e}")
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except:
                    pass
                return False
            
            logger.info(f"✓ Конфиг сохранён: {self.config_path}")
            return True
        
        except Exception as e:
            logger.error(f"✗ Критическая ошибка save: {e}")
            return False
    
    def _deep_merge(self, target: Dict, source: Dict) -> None:
        """
        Глубокое слияние конфигов
        """
        if not isinstance(target, dict) or not isinstance(source, dict):
            return
        
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Получить значение из конфига
        """
        if not isinstance(key, str) or not key:
            return default
        
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value if value is not None else default
    
    def set(self, key: str, value: Any) -> bool:
        """
        Установить значение в конфиг
        """
        if not isinstance(key, str) or not key:
            logger.error(f"✗ key должен быть непустой строкой")
            return False
        
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            elif not isinstance(config[k], dict):
                logger.error(f"✗ Путь '{k}' не dict")
                return False
            
            config = config[k]
        
        config[keys[-1]] = value
        logger.debug(f"✓ Конфиг обновлен: {key} = {value}")
        return True
    
    def merge(self, updates: Dict) -> bool:
        """
        Слить обновления в конфиг
        """
        try:
            if not isinstance(updates, dict):
                logger.error(f"✗ updates должен быть dict")
                return False
            
            self._deep_merge(self.config, updates)
            logger.info(f"✓ Конфиг обновлен (merge)")
            return True
        
        except Exception as e:
            logger.error(f"✗ Ошибка merge: {e}")
            return False