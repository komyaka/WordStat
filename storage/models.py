"""
Модели данных для приложения (ТРОЙНАЯ ПРОВЕРКА)
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime

@dataclass
class KeywordData:
    """Данные ключевого слова"""
    phrase: str
    count: int
    seed: str
    depth: int
    source: Optional[str] = None
    geo_tokens: List[str] = field(default_factory=list)
    intent: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    origin: str = "API"
    
    def to_dict(self) -> Dict:
        """Конвертировать в dict"""
        return {
            'phrase': self.phrase,
            'count': self.count,
            'seed': self.seed,
            'depth': self.depth,
            'source': self.source,
            'geo_tokens': list(self.geo_tokens),
            'intent': self.intent,
            'timestamp': self.timestamp,
            'origin': self.origin,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'KeywordData':
        """Создать из dict"""
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data)}")
        
        # Safe conversion to int for count and depth
        try:
            count_val = data.get('count', 0)
            count = int(count_val) if count_val is not None else 0
        except (ValueError, TypeError):
            count = 0
        
        try:
            depth_val = data.get('depth', 1)
            depth = int(depth_val) if depth_val is not None else 1
        except (ValueError, TypeError):
            depth = 1
        
        return cls(
            phrase=str(data.get('phrase', '')),
            count=count,
            seed=str(data.get('seed', '')),
            depth=depth,
            source=data.get('source'),
            geo_tokens=list(data.get('geo_tokens', [])),
            intent=data.get('intent'),
            timestamp=str(data.get('timestamp', datetime.now().isoformat())),
            origin=str(data.get('origin', 'API')),
        )

@dataclass
class TaskItem:
    """Элемент очереди задач"""
    phrase: str
    depth: int
    seed: str
    source: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Конвертировать в dict"""
        return {
            'phrase': self.phrase,
            'depth': self.depth,
            'seed': self.seed,
            'source': self.source,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TaskItem':
        """Создать из dict"""
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data)}")
        
        return cls(
            phrase=data.get('phrase', ''),
            depth=int(data.get('depth', 1)),
            seed=data.get('seed', ''),
            source=data.get('source'),
        )

@dataclass
class SessionState:
    """Состояние сессии (для resume/checkpoint)"""
    task_queue: List[Dict] = field(default_factory=list)
    queried_phrases: Set[str] = field(default_factory=set)
    enqueued_phrases: Set[str] = field(default_factory=set)
    keywords: Dict[str, KeywordData] = field(default_factory=dict)
    
    rps_counter: List[float] = field(default_factory=list)
    hour_count: int = 0
    hour_window_start: Optional[float] = None
    day_count: int = 0
    day_window_start: Optional[float] = None
    
    session_start: float = field(default_factory=lambda: datetime.now().timestamp())
    completed_requests: int = 0
    
    def to_dict(self) -> Dict:
        """Конвертировать в dict для JSON сохранения"""
        return {
            'task_queue': list(self.task_queue),
            'queried_phrases': list(self.queried_phrases),
            'enqueued_phrases': list(self.enqueued_phrases),
            'keywords': {
                k: (v.to_dict() if isinstance(v, KeywordData) else v)
                for k, v in self.keywords.items()
            },
            'rps_counter': list(self.rps_counter),
            'hour_count': int(self.hour_count),
            'hour_window_start': self.hour_window_start,
            'day_count': int(self.day_count),
            'day_window_start': self.day_window_start,
            'session_start': round(self.session_start, 2),
            'completed_requests': int(self.completed_requests),
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SessionState':
        """Создать из dict"""
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data)}")
        
        state = cls()
        state.task_queue = list(data.get('task_queue', []))
        state.queried_phrases = set(data.get('queried_phrases', []))
        state.enqueued_phrases = set(data.get('enqueued_phrases', []))
        
        keywords_data = data.get('keywords', {})
        state.keywords = {}
        for k, v in keywords_data.items():
            try:
                if isinstance(v, dict):
                    state.keywords[k] = KeywordData.from_dict(v)
                elif isinstance(v, KeywordData):
                    state.keywords[k] = v
            except Exception as e:
                # Логировать ошибку но не падать
                print(f"Warning: ошибка восстановления ключевого слова {k}: {e}")
        
        state.rps_counter = list(data.get('rps_counter', []))
        state.hour_count = int(data.get('hour_count', 0))
        state.hour_window_start = data.get('hour_window_start')
        state.day_count = int(data.get('day_count', 0))
        state.day_window_start = data.get('day_window_start')
        state.session_start = float(data.get('session_start', datetime.now().timestamp()))
        state.completed_requests = int(data.get('completed_requests', 0))
        
        return state

@dataclass
class APIResponse:
    """Структурированный ответ API"""
    results: List[Dict] = field(default_factory=list)
    associations: List[Dict] = field(default_factory=list)
    status_code: int = 200
    error: Optional[str] = None