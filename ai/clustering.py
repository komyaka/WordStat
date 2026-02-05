"""
Семантический анализ и кластеризация ключевых слов
ВЕРСИЯ 2.0: С поддержкой Sentence-Transformers и HDBSCAN
"""
import threading
from typing import Dict, List, Set, Tuple, Optional
import numpy as np
from collections import defaultdict
import re

from utils.logger import get_logger
from storage.models import KeywordData

logger = get_logger('WordStat.AI.Clustering')

# ============================================================================
# ПРОВЕРКА ДОСТУПНЫХ БИБЛИОТЕК
# ============================================================================

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import KMeans, AgglomerativeClustering
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("⚠ scikit-learn не установлен, кластеризация отключена")
    SKLEARN_AVAILABLE = False

try:
    import pymorphy3
    MORPH_AVAILABLE = True
except ImportError:
    logger.warning("⚠ pymorphy3 не установлен, лемматизация отключена")
    MORPH_AVAILABLE = False

# ✅ SENTENCE-TRANSFORMERS - ЛУЧШИЙ ВАРИАНТ ДЛЯ СЕМАНТИКИ
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
    logger.info("✓ sentence-transformers доступен - семантический анализ включён")
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("⚠ sentence-transformers не установлен, используем TF-IDF")

# ✅ HDBSCAN - ЛУЧШИЙ АЛГОРИТМ КЛАСТЕРИЗАЦИИ
try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
    logger.info("✓ HDBSCAN доступен - улучшенная кластеризация включена")
except ImportError:
    HDBSCAN_AVAILABLE = False
    logger.warning("⚠ hdbscan не установлен, используем Agglomerative")

# Русские стоп-слова для фильтрации
RUSSIAN_STOP_WORDS = {
    'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все',
    'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по',
    'только', 'её', 'мне', 'было', 'вот', 'от', 'меня', 'ещё', 'нет', 'о', 'из', 'ему',
    'теперь', 'когда', 'уже', 'для', 'вас', 'нибудь', 'был', 'чего', 'тут', 'здесь',
    'если', 'их', 'или', 'ни', 'быть', 'при', 'чем', 'без', 'до', 'под', 'над', 'об'
}


class SemanticAnalyzer:
    """
    Продвинутый семантический анализатор с поддержкой:
    - Sentence-Transformers (мультиязычные эмбеддинги)
    - HDBSCAN (автоматическое обнаружение кластеров)
    - Fallback на TF-IDF + Agglomerative
    """
    
    # Лучшие модели для русского языка
    EMBEDDING_MODELS = {
        'multilingual': 'paraphrase-multilingual-MiniLM-L12-v2',  # Быстрая, хорошее качество
        'multilingual_large': 'paraphrase-multilingual-mpnet-base-v2',  # Лучшее качество
        'labse': 'sentence-transformers/LaBSE',  # Отличная для русского
    }
    
    def __init__(self, 
                 lemmatize: bool = True, 
                 max_features: int = 1000,
                 embedding_model: str = 'multilingual',
                 use_semantic: bool = True):
        """
        Args:
            lemmatize: Использовать лемматизацию для TF-IDF
            max_features: Максимум признаков TF-IDF (fallback)
            embedding_model: Модель эмбеддингов ('multilingual', 'multilingual_large', 'labse')
            use_semantic: Использовать семантические эмбеддинги (если доступны)
        """
        try:
            self.lemmatize = lemmatize and MORPH_AVAILABLE
            self.max_features = max_features
            self.use_semantic = use_semantic and SENTENCE_TRANSFORMERS_AVAILABLE
            self._last_clusters = {}
            self._clustering_method = 'unknown'
            
            # ✅ ИНИЦИАЛИЗАЦИЯ МОРФОЛОГИЧЕСКОГО АНАЛИЗАТОРА
            if self.lemmatize:
                self.morph = pymorphy3.MorphAnalyzer()
            else:
                self.morph = None
            
            # ✅ ИНИЦИАЛИЗАЦИЯ SENTENCE-TRANSFORMERS
            self.sentence_model = None
            if self.use_semantic:
                model_name = self.EMBEDDING_MODELS.get(embedding_model, 
                                                       self.EMBEDDING_MODELS['multilingual'])
                try:
                    logger.info(f"🔄 Загружаю модель эмбеддингов: {model_name}...")
                    self.sentence_model = SentenceTransformer(model_name)
                    logger.info(f"✓ Модель загружена: {model_name}")
                except Exception as e:
                    logger.warning(f"⚠ Ошибка загрузки модели: {e}, используем TF-IDF")
                    self.use_semantic = False
                    self.sentence_model = None
            
            self.vectorizer = None
            self.lock = threading.RLock()
            
            method = "Sentence-Transformers + HDBSCAN" if self.use_semantic else "TF-IDF + Agglomerative"
            logger.info(f"✓ SemanticAnalyzer инициализирован ({method})")
        
        except Exception as e:
            logger.error(f"✗ Ошибка инициализации SemanticAnalyzer: {e}")
            self.lemmatize = False
            self.morph = None
            self.use_semantic = False
            self.sentence_model = None
            self._last_clusters = {}
    
    def _lemmatize_text(self, text: str, remove_stop_words: bool = True) -> str:
        """Лемматизировать текст и удалить стоп-слова"""
        try:
            words = text.lower().split()
            result_words = []
            
            for word in words:
                if remove_stop_words and word in RUSSIAN_STOP_WORDS:
                    continue
                
                try:
                    if self.lemmatize and self.morph:
                        parsed = self.morph.parse(word)[0]
                        lemma = parsed.normal_form
                        result_words.append(lemma)
                    else:
                        result_words.append(word)
                except Exception:
                    result_words.append(word)
            
            return ' '.join(result_words)
        
        except Exception as e:
            logger.debug(f"⚠ Ошибка лемматизации: {e}")
            return text
    
    def _get_semantic_embeddings(self, phrases: List[str]) -> np.ndarray:
        """
        Получить семантические эмбеддинги с помощью Sentence-Transformers.
        Это ЛУЧШИЙ метод для понимания смысла фраз.
        """
        try:
            if not self.sentence_model:
                raise ValueError("Sentence model не инициализирован")
            
            logger.info(f"🧠 Генерирую семантические эмбеддинги для {len(phrases)} фраз...")
            
            # Sentence-Transformers автоматически обрабатывает батчи
            embeddings = self.sentence_model.encode(
                phrases,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True  # L2 нормализация для косинусного сходства
            )
            
            logger.info(f"✓ Эмбеддинги созданы: {embeddings.shape}")
            return embeddings
        
        except Exception as e:
            logger.error(f"✗ Ошибка генерации эмбеддингов: {e}")
            raise
    
    def _get_tfidf_embeddings(self, phrases: List[str]) -> np.ndarray:
        """
        Fallback: Получить TF-IDF эмбеддинги.
        Используется когда sentence-transformers недоступен.
        """
        try:
            # Лемматизируем для лучшего TF-IDF
            processed_phrases = [self._lemmatize_text(p) for p in phrases]
            
            vectorizer = TfidfVectorizer(
                max_features=self.max_features,
                ngram_range=(1, 3),
                lowercase=True,
                strip_accents='unicode',
                min_df=1,
                max_df=0.95,
                sublinear_tf=True
            )
            
            tfidf_matrix = vectorizer.fit_transform(processed_phrases)
            logger.info(f"✓ TF-IDF матрица создана: {tfidf_matrix.shape}")
            
            return tfidf_matrix.toarray()
        
        except Exception as e:
            logger.error(f"✗ Ошибка TF-IDF: {e}")
            raise
    
    def _cluster_hdbscan(self, embeddings: np.ndarray, 
                         min_cluster_size: int = 2,
                         min_samples: int = 1) -> np.ndarray:
        """
        Кластеризация HDBSCAN - автоматически определяет количество кластеров.
        Лучший алгоритм для семантической кластеризации.
        """
        try:
            logger.info(f"🎯 HDBSCAN кластеризация (min_cluster_size={min_cluster_size})...")
            
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=min_cluster_size,
                min_samples=min_samples,
                metric='euclidean',
                cluster_selection_method='eom',  # Excess of Mass
                prediction_data=True
            )
            
            labels = clusterer.fit_predict(embeddings)
            
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            n_noise = list(labels).count(-1)
            
            logger.info(f"✓ HDBSCAN: {n_clusters} кластеров, {n_noise} некластеризованных")
            
            return labels
        
        except Exception as e:
            logger.error(f"✗ Ошибка HDBSCAN: {e}")
            raise
    
    def _cluster_agglomerative(self, embeddings: np.ndarray,
                               n_clusters: int) -> np.ndarray:
        """
        Fallback: Agglomerative Clustering с заданным количеством кластеров.
        """
        try:
            actual_n_clusters = min(n_clusters, len(embeddings))
            if actual_n_clusters < 1:
                actual_n_clusters = 1
            
            logger.info(f"🎯 Agglomerative кластеризация: {actual_n_clusters} кластеров")
            
            clustering = AgglomerativeClustering(
                n_clusters=actual_n_clusters,
                metric='euclidean',
                linkage='ward'
            )
            
            labels = clustering.fit_predict(embeddings)
            
            logger.info(f"✓ Agglomerative: {len(set(labels))} кластеров")
            
            return labels
        
        except Exception as e:
            logger.error(f"✗ Ошибка Agglomerative: {e}")
            raise
    
    def _cluster_threshold(self, phrases: List[str], 
                          similarity_matrix: np.ndarray,
                          threshold: float = 0.5) -> Dict[str, List[str]]:
        """Кластеризация по порогу сходства (для режима threshold)"""
        try:
            logger.info(f"🔗 Кластеризация по порогу: {threshold}")
            
            clusters = {}
            assigned = set()
            
            for i, phrase in enumerate(phrases):
                if i in assigned:
                    continue
                
                similar = [i]
                for j in range(i + 1, len(phrases)):
                    if j not in assigned and similarity_matrix[i, j] >= threshold:
                        similar.append(j)
                        assigned.add(j)
                
                assigned.add(i)
                
                center_phrase = phrase
                cluster_phrases = [phrases[idx] for idx in similar]
                clusters[center_phrase] = cluster_phrases
            
            return clusters
        
        except Exception as e:
            logger.error(f"✗ Ошибка _cluster_threshold: {e}")
            return {}
    
    def analyze(self, keywords: Dict[str, KeywordData], 
                threshold: float = 0.5, 
                n_clusters: int = 10,
                clustering_mode: str = 'auto',
                min_cluster_size: int = 2) -> Dict[str, List[str]]:
        """
        Кластеризировать ключевые слова с использованием лучших доступных методов.
        
        Args:
            keywords: Словарь ключевых слов
            threshold: Порог сходства (для threshold режима)
            n_clusters: Количество кластеров (для fixed режима)
            clustering_mode: 'auto', 'semantic', 'tfidf', 'threshold', 'fixed'
            min_cluster_size: Минимальный размер кластера
        
        Returns:
            Словарь кластеров {центр: [ключевые слова]}
        """
        try:
            if not keywords:
                logger.warning("⚠ Пусто ключевых слов для анализа")
                return {}
            
            if not SKLEARN_AVAILABLE:
                logger.warning("⚠ scikit-learn не доступен")
                return {'основной': list(keywords.keys())}
            
            logger.info(f"🤖 Начинаю AI анализ: {len(keywords)} ключевых слов")
            logger.info(f"   Mode: {clustering_mode}, threshold: {threshold}, n_clusters: {n_clusters}")
            
            with self.lock:
                phrases = list(keywords.keys())
                
                if len(phrases) < 2:
                    logger.warning("⚠ Недостаточно фраз для кластеризации")
                    return {'Другое': phrases} if phrases else {}
                
                # ✅ ВЫБОР МЕТОДА ЭМБЕДДИНГОВ
                if clustering_mode in ['auto', 'semantic'] and self.use_semantic:
                    # ЛУЧШИЙ ВАРИАНТ: Sentence-Transformers
                    logger.info("🧠 Используем Sentence-Transformers (семантические эмбеддинги)")
                    self._clustering_method = 'Sentence-Transformers'
                    embeddings = self._get_semantic_embeddings(phrases)
                else:
                    # Fallback: TF-IDF
                    logger.info("📊 Используем TF-IDF (лексические эмбеддинги)")
                    self._clustering_method = 'TF-IDF'
                    embeddings = self._get_tfidf_embeddings(phrases)
                
                # ✅ ВЫБОР МЕТОДА КЛАСТЕРИЗАЦИИ
                if clustering_mode == 'threshold':
                    # Порог сходства
                    similarity_matrix = cosine_similarity(embeddings)
                    clusters = self._cluster_threshold(phrases, similarity_matrix, threshold)
                
                elif clustering_mode == 'fixed':
                    # Фиксированное количество кластеров
                    labels = self._cluster_agglomerative(embeddings, n_clusters)
                    clusters = self._labels_to_clusters(phrases, labels)
                
                elif clustering_mode in ['auto', 'semantic'] and HDBSCAN_AVAILABLE:
                    # ЛУЧШИЙ ВАРИАНТ: HDBSCAN
                    logger.info("🎯 Используем HDBSCAN (автоматическое определение кластеров)")
                    self._clustering_method += ' + HDBSCAN'
                    labels = self._cluster_hdbscan(embeddings, min_cluster_size=min_cluster_size)
                    clusters = self._labels_to_clusters(phrases, labels)
                
                else:
                    # Fallback: Agglomerative
                    labels = self._cluster_agglomerative(embeddings, n_clusters)
                    clusters = self._labels_to_clusters(phrases, labels)
                
                # ✅ ПРИМЕНИТЬ МИНИМАЛЬНЫЙ РАЗМЕР КЛАСТЕРА
                clusters = self._enforce_min_cluster_size(clusters, min_cluster_size)
                
                logger.info(f"✓ Кластеризация завершена: {len(clusters)} кластеров ({self._clustering_method})")
                
                self._last_clusters = clusters
                return clusters
        
        except Exception as e:
            logger.error(f"✗ Ошибка анализа: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _labels_to_clusters(self, phrases: List[str], 
                           labels: np.ndarray) -> Dict[str, List[str]]:
        """Преобразовать метки кластеров в словарь"""
        try:
            clusters_dict = defaultdict(list)
            
            for phrase, label in zip(phrases, labels):
                if label == -1:
                    # HDBSCAN: некластеризованные -> "Другое"
                    clusters_dict['Другое'].append(phrase)
                else:
                    clusters_dict[label].append(phrase)
            
            # Преобразуем в формат {center: [phrases]}
            result = {}
            for label, cluster_phrases in clusters_dict.items():
                if label == 'Другое':
                    result['Другое'] = cluster_phrases
                else:
                    center = cluster_phrases[0]  # Первая фраза как центр
                    result[center] = cluster_phrases
            
            return result
        
        except Exception as e:
            logger.error(f"✗ Ошибка _labels_to_clusters: {e}")
            return {}
    
    def _enforce_min_cluster_size(self, clusters: Dict[str, List[str]], 
                                   min_size: int = 2) -> Dict[str, List[str]]:
        """
        Применить минимальный размер кластера.
        Кластеры с менее чем min_size ключей объединяются в 'Другое'.
        """
        try:
            if not clusters:
                return {}
            
            logger.info(f"🔧 Применяю минимальный размер кластера: {min_size}")
            
            result = {}
            other_phrases = clusters.get('Другое', []).copy()
            
            for center, phrases in clusters.items():
                if center == 'Другое':
                    continue
                    
                if len(phrases) >= min_size:
                    result[center] = phrases
                else:
                    other_phrases.extend(phrases)
                    logger.debug(f"   Кластер '{center}' ({len(phrases)} фраз) -> Другое")
            
            if other_phrases:
                result['Другое'] = other_phrases
                logger.info(f"   📦 Кластер 'Другое': {len(other_phrases)} фраз")
            
            logger.info(f"✓ После фильтрации: {len(result)} кластеров")
            return result
        
        except Exception as e:
            logger.error(f"✗ Ошибка _enforce_min_cluster_size: {e}")
            return clusters
    
    def get_clustering_method(self) -> str:
        """Получить название использованного метода кластеризации"""
        return getattr(self, '_clustering_method', 'unknown')
    
    def get_last_clusters(self) -> Dict[str, List[str]]:
        """Получить последние результаты кластеризации"""
        return getattr(self, '_last_clusters', {})
    
    def get_cluster_stats(self, clusters: Dict[str, List[str]]) -> Dict:
        """Получить статистику кластеров"""
        try:
            if not clusters:
                return {}
            
            stats = {
                'total_clusters': len(clusters),
                'total_keywords': sum(len(v) for v in clusters.values()),
                'avg_cluster_size': sum(len(v) for v in clusters.values()) / len(clusters) if clusters else 0,
                'max_cluster_size': max(len(v) for v in clusters.values()) if clusters else 0,
                'min_cluster_size': min(len(v) for v in clusters.values()) if clusters else 0,
                'clustering_method': self.get_clustering_method(),
            }
            
            return stats
        
        except Exception as e:
            logger.error(f"✗ Ошибка get_cluster_stats: {e}")
            return {}
    
    def format_clusters(self, clusters: Dict[str, List[str]]) -> str:
        """Форматировать кластеры для вывода"""
        try:
            if not clusters:
                return "Кластеры не найдены"
            
            output = []
            output.append("=" * 80)
            output.append(f"РЕЗУЛЬТАТЫ КЛАСТЕРИЗАЦИИ ({self.get_clustering_method()})")
            output.append("=" * 80)
            
            for idx, (center, phrases) in enumerate(clusters.items(), 1):
                output.append(f"\n🎯 Кластер {idx}: '{center}'")
                output.append(f"   📊 Размер: {len(phrases)} фраз")
                output.append(f"   📋 Фразы:")
                
                for phrase in phrases[:10]:
                    output.append(f"      • {phrase}")
                
                if len(phrases) > 10:
                    output.append(f"      ... и ещё {len(phrases) - 10} фраз")
            
            output.append("\n" + "=" * 80)
            
            return "\n".join(output)
        
        except Exception as e:
            logger.error(f"✗ Ошибка format_clusters: {e}")
            return str(clusters)
    
    def format_clusters_for_export(self, clusters: Dict[str, List[str]]) -> str:
        """Форматировать кластеры для экспорта (полный список)"""
        try:
            if not clusters:
                return "Кластеры не найдены"
            
            output = []
            output.append(f"РЕЗУЛЬТАТЫ AI КЛАСТЕРИЗАЦИИ ({self.get_clustering_method()})")
            output.append("=" * 80)
            output.append("")
            
            for idx, (center, phrases) in enumerate(clusters.items(), 1):
                output.append(f"КЛАСТЕР {idx}: {center}")
                output.append(f"Количество: {len(phrases)}")
                output.append("-" * 40)
                
                for phrase in phrases:
                    output.append(f"  {phrase}")
                
                output.append("")
            
            output.append("=" * 80)
            
            return "\n".join(output)
        
        except Exception as e:
            logger.error(f"✗ Ошибка format_clusters_for_export: {e}")
            return str(clusters)
    
    def export_clusters_tsv(self, clusters: Dict[str, List[str]]) -> str:
        """Экспортировать кластеры в TSV формат"""
        try:
            if not clusters:
                return ""
            
            lines = ["Кластер\tФраза"]
            
            for center, phrases in clusters.items():
                for phrase in phrases:
                    lines.append(f"{center}\t{phrase}")
            
            return "\n".join(lines)
        
        except Exception as e:
            logger.error(f"✗ Ошибка export_clusters_tsv: {e}")
            return ""
    
    @staticmethod
    def is_semantic_available() -> bool:
        """Проверить доступность семантического анализа"""
        return SENTENCE_TRANSFORMERS_AVAILABLE
    
    @staticmethod
    def is_hdbscan_available() -> bool:
        """Проверить доступность HDBSCAN"""
        return HDBSCAN_AVAILABLE
    
    @staticmethod
    def get_available_methods() -> List[str]:
        """Получить список доступных методов кластеризации"""
        methods = ['tfidf', 'threshold', 'fixed']
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            methods.insert(0, 'semantic')
            methods.insert(0, 'auto')
        
        return methods