"""
Семантический анализ и кластеризация ключевых слов
ВЕРСИЯ 2.0: С поддержкой Sentence-Transformers и HDBSCAN
"""
import threading
import time
from typing import Callable, Dict, List, Set, Tuple, Optional
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
except SyntaxError as e:
    logger.error(f"⚠ scikit-learn повреждён: {e}")
    SKLEARN_AVAILABLE = False

try:
    import pymorphy3
    MORPH_AVAILABLE = True
except ImportError:
    logger.warning("⚠ pymorphy3 не установлен, лемматизация отключена")
    MORPH_AVAILABLE = False
except SyntaxError as e:
    logger.error(f"⚠ pymorphy3 повреждён: {e}")
    MORPH_AVAILABLE = False

# ✅ SENTENCE-TRANSFORMERS - ЛУЧШИЙ ВАРИАНТ ДЛЯ СЕМАНТИКИ
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
    logger.info("✓ sentence-transformers доступен - семантический анализ включён")
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("⚠ sentence-transformers не установлен, используем TF-IDF")
except SyntaxError as e:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.error(f"⚠ sentence-transformers повреждён (null bytes или ошибка синтаксиса): {e}")
    logger.error("Попробуйте переустановить: pip uninstall sentence-transformers && pip install sentence-transformers")
except Exception as e:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    error_msg = str(e).lower()
    if 'keras 3' in error_msg or 'tf-keras' in error_msg:
        logger.error(f"⚠ sentence-transformers недоступен: конфликт Keras 3 с transformers")
        logger.error("Решение: pip install tf-keras")
        logger.error("Или удалите tensorflow, если он не нужен: pip uninstall tensorflow keras")
    else:
        logger.error(f"⚠ sentence-transformers недоступен (ошибка: {type(e).__name__}: {e})")
        logger.error("Попробуйте переустановить: pip uninstall sentence-transformers && pip install sentence-transformers")

# ✅ HDBSCAN - ЛУЧШИЙ АЛГОРИТМ КЛАСТЕРИЗАЦИИ
try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
    logger.info("✓ HDBSCAN доступен - улучшенная кластеризация включена")
except ImportError:
    HDBSCAN_AVAILABLE = False
    logger.warning("⚠ hdbscan не установлен, используем Agglomerative")
except SyntaxError as e:
    logger.error(f"⚠ hdbscan повреждён: {e}")
    HDBSCAN_AVAILABLE = False

# ✅ LEIDEN - ГРАФОВАЯ КЛАСТЕРИЗАЦИЯ
try:
    import igraph as ig
    import leidenalg
    LEIDEN_AVAILABLE = True
    logger.info("✓ Leiden доступен - графовая кластеризация включена")
except ImportError:
    LEIDEN_AVAILABLE = False
    logger.warning("⚠ leidenalg/igraph не установлены, Leiden недоступен")
except Exception as e:
    LEIDEN_AVAILABLE = False
    logger.error(f"⚠ Leiden недоступен: {e}")

# ✅ ОПРЕДЕЛЕНИЕ УСТРОЙСТВА (CPU / GPU)
try:
    import torch
    _TORCH_DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
    if _TORCH_DEVICE == 'cuda':
        logger.info(f"✓ GPU доступен: {torch.cuda.get_device_name(0)} — используем CUDA для эмбеддингов")
    else:
        logger.info("ℹ GPU не обнаружен — используем CPU для эмбеддингов")
except Exception:
    _TORCH_DEVICE = 'cpu'

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
        # 🏆 ЛУЧШИЕ для русского (2025-2026)
        'bge-m3': 'BAAI/bge-m3',
        'user-bge-m3': 'deepvk/USER-bge-m3',
        'e5-large': 'intfloat/multilingual-e5-large-instruct',
        # ✅ ХОРОШИЕ (баланс скорость/качество)
        'labse-ru': 'sergeyzh/LaBSE-ru-sts',
        'labse': 'sentence-transformers/LaBSE',
        # ⚡ БЫСТРЫЕ (слабое железо)
        'multilingual': 'paraphrase-multilingual-MiniLM-L12-v2',
        'multilingual_large': 'paraphrase-multilingual-mpnet-base-v2',
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
                    logger.info(f"🔄 Загружаю модель эмбеддингов: {model_name} (device={_TORCH_DEVICE})...")
                    self.sentence_model = SentenceTransformer(model_name, device=_TORCH_DEVICE)
                    logger.info(f"✓ Модель загружена: {model_name} на {_TORCH_DEVICE}")
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
            
            # Use batching for large datasets
            batch_size = 256 if _TORCH_DEVICE == 'cuda' else 128

            embeddings = self.sentence_model.encode(
                phrases,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,  # L2 нормализация для косинусного сходства
                batch_size=batch_size
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
        """Кластеризация по порогу сходства — оптимизированная версия"""
        try:
            logger.info(f"🔗 Кластеризация по порогу: {threshold} ({len(phrases)} фраз)")
            
            n = len(phrases)
            clusters = {}
            assigned = np.zeros(n, dtype=bool)
            
            for i in range(n):
                if assigned[i]:
                    continue
                
                # Vectorized: find all similar unassigned phrases
                mask = (~assigned) & (similarity_matrix[i] >= threshold)
                mask[i] = True  # include self
                similar_indices = np.where(mask)[0]
                
                assigned[similar_indices] = True
                
                center_phrase = phrases[i]
                cluster_phrases = [phrases[idx] for idx in similar_indices]
                clusters[center_phrase] = cluster_phrases
            
            return clusters
        
        except Exception as e:
            logger.error(f"✗ Ошибка _cluster_threshold: {e}")
            return {}
    
    def _compute_similarity_chunked(self, embeddings: np.ndarray, chunk_size: int = 5000) -> np.ndarray:
        """Compute cosine similarity in chunks to reduce memory usage."""
        n = len(embeddings)
        if n <= chunk_size:
            return cosine_similarity(embeddings)
        
        logger.info(f"🧮 Вычисляю матрицу сходства по частям ({n}x{n})...")
        similarity = np.zeros((n, n), dtype=np.float32)
        
        for i in range(0, n, chunk_size):
            end_i = min(i + chunk_size, n)
            for j in range(i, n, chunk_size):
                end_j = min(j + chunk_size, n)
                block = cosine_similarity(embeddings[i:end_i], embeddings[j:end_j])
                similarity[i:end_i, j:end_j] = block
                if i != j:
                    similarity[j:end_j, i:end_i] = block.T
        
        return similarity

    def _cluster_leiden(self, embeddings: np.ndarray, threshold: float = 0.3) -> np.ndarray:
        """Leiden графовая кластеризация — лучший для SEO."""
        similarity = self._compute_similarity_chunked(embeddings)
        n = len(similarity)
        i_indices, j_indices = np.triu_indices(n, k=1)
        mask = similarity[i_indices, j_indices] >= threshold
        edges = list(zip(i_indices[mask].tolist(), j_indices[mask].tolist()))
        weights = similarity[i_indices[mask], j_indices[mask]].tolist()
        
        if not edges:
            return np.zeros(n, dtype=int)
        
        graph = ig.Graph(n=n, edges=edges)
        graph.es['weight'] = weights
        partition = leidenalg.find_partition(
            graph, leidenalg.ModularityVertexPartition, weights='weight'
        )
        return np.array(partition.membership)

    def analyze(self, keywords: Dict[str, KeywordData], 
                threshold: float = 0.5, 
                n_clusters: int = 10,
                clustering_mode: str = 'auto',
                min_cluster_size: int = 2,
                progress_callback: Optional[Callable[[int, str], None]] = None) -> Dict[str, List[str]]:
        """
        Кластеризировать ключевые слова с использованием лучших доступных методов.
        
        Args:
            keywords: Словарь ключевых слов
            threshold: Порог сходства (для threshold режима)
            n_clusters: Количество кластеров (для fixed режима)
            clustering_mode: 'auto', 'semantic', 'tfidf', 'threshold', 'fixed', 'leiden'
            min_cluster_size: Минимальный размер кластера
            progress_callback: Опциональный callback(percent: int, message: str)
        
        Returns:
            Словарь кластеров {центр: [ключевые слова]}
        """
        def _report(pct: int, msg: str) -> None:
            if progress_callback:
                try:
                    progress_callback(pct, msg)
                except Exception as cb_exc:
                    logger.debug(f"⚠ Ошибка progress_callback: {cb_exc}")

        try:
            if not keywords:
                logger.warning("⚠ Пусто ключевых слов для анализа")
                return {}
            
            if not SKLEARN_AVAILABLE:
                logger.warning("⚠ scikit-learn не доступен")
                return {'основной': list(keywords.keys())}
            
            logger.info(f"🤖 Начинаю AI анализ: {len(keywords)} ключевых слов")
            logger.info(f"   Mode: {clustering_mode}, threshold: {threshold}, n_clusters: {n_clusters}")
            
            _report(5, "Подготовка данных...")
            _start_time = time.monotonic()

            with self.lock:
                phrases = list(keywords.keys())
                
                if len(phrases) < 2:
                    logger.warning("⚠ Недостаточно фраз для кластеризации")
                    return {'Другое': phrases} if phrases else {}
                
                # ✅ ВЫБОР МЕТОДА ЭМБЕДДИНГОВ (независимо от режима кластеризации)
                if clustering_mode != 'tfidf' and self.use_semantic:
                    # Sentence-Transformers для всех режимов, кроме явного tfidf
                    logger.info("🧠 Используем Sentence-Transformers (семантические эмбеддинги)")
                    self._clustering_method = 'Sentence-Transformers'
                    _report(15, f"Генерация эмбеддингов ({_TORCH_DEVICE.upper()})...")
                    embeddings = self._get_semantic_embeddings(phrases)
                else:
                    # Fallback: TF-IDF
                    logger.info("📊 Используем TF-IDF (лексические эмбеддинги)")
                    self._clustering_method = 'TF-IDF'
                    _report(15, "Генерация TF-IDF векторов...")
                    embeddings = self._get_tfidf_embeddings(phrases)
                
                _report(55, "Кластеризация...")

                # ✅ ВЫБОР МЕТОДА КЛАСТЕРИЗАЦИИ
                if clustering_mode == 'threshold':
                    # Порог сходства (с chunked вычислением для больших датасетов)
                    similarity_matrix = self._compute_similarity_chunked(embeddings)
                    clusters = self._cluster_threshold(phrases, similarity_matrix, threshold)
                
                elif clustering_mode == 'fixed':
                    # Фиксированное количество кластеров
                    labels = self._cluster_agglomerative(embeddings, n_clusters)
                    clusters = self._labels_to_clusters(phrases, labels)
                
                elif clustering_mode == 'leiden' and LEIDEN_AVAILABLE:
                    # Leiden графовая кластеризация
                    logger.info("🕸 Используем Leiden (графовая кластеризация)")
                    self._clustering_method += ' + Leiden'
                    labels = self._cluster_leiden(embeddings, threshold=threshold)
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
                
                _report(85, "Постобработка кластеров...")

                # ✅ ПРИМЕНИТЬ МИНИМАЛЬНЫЙ РАЗМЕР КЛАСТЕРА
                clusters = self._enforce_min_cluster_size(clusters, min_cluster_size)
                
                elapsed = time.monotonic() - _start_time
                logger.info(f"✓ Кластеризация завершена: {len(clusters)} кластеров ({self._clustering_method}) за {elapsed:.1f}с")
                
                _report(100, f"Готово: {len(clusters)} кластеров за {elapsed:.1f}с")

                self._last_clusters = clusters
                return clusters
        
        except Exception as e:
            logger.error(f"✗ Ошибка анализа: {e}")
            import traceback
            traceback.print_exc()
            _report(0, f"Ошибка: {e}")
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
        
        if LEIDEN_AVAILABLE:
            methods.append('leiden')
        
        return methods