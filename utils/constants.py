"""
Константы приложения
"""

# API
DEFAULT_ENDPOINT = "https://searchapi.api.cloud.yandex.net/v2/wordstat/topRequests"
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3
DEFAULT_NUM_PHRASES = 100

# Парсинг
MIN_DEPTH = 1
MAX_DEPTH = 3
MIN_TOP_N = 1
MAX_TOP_N = 5

# UI
DEVICE_TYPES = ['all', 'desktop', 'phone', 'tablet']
GEO_MODES = ['OFF', 'REMOVE', 'EXTRACT']
CACHE_MODES = ['Включено', 'Выключено', 'Только кэш', 'Обновить кэш']

# Фильтры
NGRAM_RANGE = (1, 3)
DEFAULT_CLUSTERING_THRESHOLD = 0.5
MIN_CLUSTER_SIZE = 2

COMMERCIAL_TRIGGERS = [
    'купить', 'цена', 'заказ', 'доставка', 'оплата', 'скидка', 'распродажа',
    'где купить', 'онлайн магазин', 'интернет магазин', 'товар', 'услуга'
]

INFO_TRIGGERS = [
    'как', 'что', 'почему', 'когда', 'где', 'который', 'какой',
    'информация', 'статья', 'гайд', 'учебник', 'видео', 'урок'
]

NAVIGATIONAL_TRIGGERS = [
    'вконтакте', 'facebook', 'instagram', 'youtube', 'яндекс', 'google',
    'сайт', 'ссылка', 'страница', 'профиль', 'аккаунт', 'вход', 'личный кабинет'
]

# Таймауты
UI_UPDATE_INTERVAL_MS = 100
AUTOSAVE_INTERVAL_SEC = 30

# ✅ ПУТИ И ФАЙЛЫ
OUTPUT_DIR = "."
STATE_FILE = "output.state.json"
TSV_FILE = "output.tsv"
CONFIG_FILE = "config.json"

# ✅ CACHE
CACHE_DB_PATH = "wordstat_cache.db"
CACHE_DB = "wordstat_cache.db"
CACHE_DEFAULT_TTL_DAYS = 7
CACHE_WORKER_INTERVAL_SEC = 5

# ✅ NLP КОНСТАНТЫ
RUSSIAN_STOP_WORDS = {
    'и', 'в', 'на', 'с', 'по', 'за', 'к', 'от', 'до', 'для',
    'как', 'что', 'который', 'где', 'когда', 'почему', 'зачем',
    'а', 'но', 'или', 'ни', 'если', 'то', 'чтобы', 'так',
    'не', 'ни', 'нет', 'да', 'то', 'это', 'быть', 'иметь',
    'мы', 'вы', 'они', 'вас', 'нас', 'них', 'ему', 'ей',
    'его', 'её', 'их', 'мне', 'тебе', 'себе', 'ему', 'ей',
    'ему', 'ей', 'нему', 'которой', 'которым', 'которых',
    'при', 'между', 'среди', 'перед', 'после', 'через',
    'без', 'вне', 'вокруг', 'вдоль', 'вверх', 'вниз',
    'т', 'е', 'т.е', 'т.к', 'т.к', 'б', 'пр', 'др'
}

# ✅ ГЕО КОНСТАНТЫ
GEO_KEYWORDS = {
    'москва', 'спб', 'санкт-петербург', 'казань', 'екатеринбург',
    'новосибирск', 'воронеж', 'пермь', 'краснодар', 'ростов',
    'самара', 'уфа', 'челябинск', 'омск', 'волгоград',
    'нижний новгород', 'тверь', 'ярославль', 'рязань', 'белгород',
    'тула', 'липецк', 'смоленск', 'брянск', 'курск',
    'россия', 'российский', 'российской', 'российское', 'российском',
    'регион', 'область', 'край', 'округ', 'район',
}

# Размеры лога
LOG_MAX_ROWS = 100

# ✅ МОРФОЛОГИЯ
MORPH_ANALYZER_LANG = 'ru'

# ✅ AI
AI_DEFAULT_LEMMATIZE = True
AI_DEFAULT_MAX_FEATURES = 1000
AI_DEFAULT_THRESHOLD = 0.5
AI_DEFAULT_N_CLUSTERS = 10