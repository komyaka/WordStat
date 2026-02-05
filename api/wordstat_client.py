"""
Клиент для Yandex Cloud Search API Wordstat v2 (ФИНАЛЬНЫЙ)
"""
import requests
import time
import json
from typing import Optional, List, Dict, Tuple
from datetime import datetime

from utils.logger import get_logger
from utils.constants import DEFAULT_TIMEOUT, DEFAULT_RETRIES, DEFAULT_NUM_PHRASES
from storage.models import APIResponse
from .error_handler import ErrorHandler, APIError, ErrorType, ErrorAction

logger = get_logger('WordStat.API')


class WordstatClient:
    """Клиент для Wordstat API v2"""
    
    BASE_URL = "https://searchapi.api.cloud.yandex.net/v2/wordstat/topRequests"
    
    def __init__(self,
                 api_key: str,
                 folder_id: str,
                 timeout: int = DEFAULT_TIMEOUT,
                 max_retries: int = DEFAULT_RETRIES):
        """
        Args:
            api_key: API ключ Yandex Cloud
            folder_id: ID папки в Yandex Cloud
            timeout: Таймаут запроса (сек)
            max_retries: Максимум попыток при ошибке
        """
        if not isinstance(api_key, str) or not api_key:
            raise ValueError("api_key должен быть непустой строкой")
        if not isinstance(folder_id, str) or not folder_id:
            raise ValueError("folder_id должен быть непустой строкой")
        if timeout <= 0:
            raise ValueError("timeout должен быть > 0")
        if max_retries < 1:
            raise ValueError("max_retries должен быть >= 1")
        
        self.api_key = api_key
        self.folder_id = folder_id
        self.timeout = timeout
        self.max_retries = max_retries
        
        self.headers = {
            'Authorization': f'Api-Key {api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'WordStat-Master-AI/2026'
        }
        
        logger.info(f"✓ WordstatClient инициализирован")
    
    def _prepare_request_body(self,
                             phrase: str,
                             num_phrases: int = DEFAULT_NUM_PHRASES) -> Dict:
        """Подготовить тело запроса"""
        
        if not isinstance(phrase, str):
            raise ValueError("phrase должен быть строкой")
        if num_phrases < 1 or num_phrases > 2000:
            raise ValueError("num_phrases должен быть 1-2000")
        
        body = {
            'phrase': phrase,
            'page': 0,
            'limit': num_phrases,
        }
        
        return body
    
    def get_wordstat(self,
                    phrase: str,
                    num_phrases: int = DEFAULT_NUM_PHRASES,
                    regions: Optional[List[int]] = None,
                    device: str = 'all') -> APIResponse:
        """
        Получить Wordstat данные
        """
        
        body = self._prepare_request_body(phrase, num_phrases)
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"[Попытка {attempt + 1}/{self.max_retries}] Запрос: '{phrase}'")
                
                response = requests.post(
                    self.BASE_URL,
                    json=body,
                    headers=self.headers,
                    timeout=self.timeout
                )
                
                # Успешный ответ
                if response.status_code == 200:
                    data = response.json()
                    
                    # ✅ Правильная структура: results + associations
                    results = data.get('results', [])
                    associations = data.get('associations', [])
                    
                    # Преобразовать count из строки в число
                    for item in results:
                        if 'count' in item and isinstance(item['count'], str):
                            try:
                                item['count'] = int(item['count'])
                            except (ValueError, TypeError):
                                item['count'] = 0
                    
                    for item in associations:
                        if 'count' in item and isinstance(item['count'], str):
                            try:
                                item['count'] = int(item['count'])
                            except (ValueError, TypeError):
                                item['count'] = 0
                    
                    logger.info(f"✓ Успех: '{phrase}' (результатов: {len(results)}, ассоциаций: {len(associations)})")
                    
                    return APIResponse(
                        results=results,
                        associations=associations,
                        status_code=200
                    )
                
                # Обработка ошибок
                else:
                    error_text = response.text[:200]
                    error_type = ErrorHandler.classify_error(response.status_code)
                    error_msg = f"HTTP {response.status_code}: {error_text}"
                    error = APIError(error_type, error_msg, response.status_code)
                    
                    logger.warning(f"⚠ {error_msg}")
                    
                    if error_type == ErrorType.AUTH_ERROR:
                        logger.error(f"✗ Ошибка аутентификации")
                        raise error
                    
                    if error_type == ErrorType.CLIENT_ERROR:
                        logger.error(f"✗ Ошибка клиента")
                        raise error
                    
                    # Для других ошибок - повторить
                    if attempt < self.max_retries - 1:
                        delay = 2 ** attempt
                        logger.warning(f"⚠ Повторная попытка через {delay}с...")
                        time.sleep(delay)
                    else:
                        raise error
            
            except requests.exceptions.Timeout:
                error = APIError(ErrorType.TIMEOUT, f"Таймаут ({self.timeout}с)")
                logger.warning(f"⚠ Таймаут")
                
                if attempt < self.max_retries - 1:
                    delay = 2 ** attempt
                    logger.warning(f"⚠ Повторная попытка через {delay}с...")
                    time.sleep(delay)
                else:
                    raise error
            
            except requests.exceptions.ConnectionError as e:
                error = APIError(ErrorType.NETWORK_ERROR, f"Ошибка соединения")
                logger.error(f"✗ {error}")
                raise error
            
            except Exception as e:
                error = APIError(ErrorType.UNKNOWN, f"Ошибка: {str(e)}")
                logger.error(f"✗ {error}")
                raise error
        
        raise APIError(ErrorType.UNKNOWN, f"Исчерпаны все попытки ({self.max_retries})")
    
    def validate_credentials(self) -> Tuple[bool, str]:
        """Проверить валидность API Key"""
        
        try:
            logger.info("🔐 Проверка учётных данных...")
            test_response = self.get_wordstat("тест", num_phrases=1)
            
            if test_response.status_code == 200:
                logger.info("✓ API учётные данные валидны")
                return True, "OK"
        
        except APIError as e:
            logger.error(f"✗ Ошибка: {e}")
            return False, str(e)
        except Exception as e:
            logger.error(f"✗ Неожиданная ошибка: {e}")
            return False, str(e)
        
        return False, "Неизвестная ошибка"