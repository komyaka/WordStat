"""
Семантический анализ и кластеризация ключевых слов
"""
import threading
from typing import Dict, List, Set, Tuple, Optional
import numpy as np
from collections import defaultdict
import re

from utils.logger import get_logger
from storage.models import KeywordData

logger = get_logger('WordStat.AI.Clustering')

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import KMeans, DBSCAN
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("⚠ scikit-learn не установлен, к��астеризация отключена")
    SKLEARN_AVAILABLE = False

try:
    import pymorphy3
    MORPH_AVAILABLE = True
except ImportError:
    logger.warning("⚠ pymorphy3 не установлен, лемматизация отключена")
    MORPH_AVAILABLE = False


class SemanticAnalyzer:
    """Семантический анализ и кластеризация"""
    
    def __init__(self, lemmatize: bool = True, max_features: int = 1000):
        """
        Args:
            lemmatize: Использовать лемматизацию
            max_features: Максимум признаков TF-IDF
        """
        try:
            self.lemmatize = lemmatize and MORPH_AVAILABLE
            self.max_features = max_features
            
            if self.lemmatize:
                self.morph = pymorphy3.MorphAnalyzer()
            else:
                self.morph = None
            
            self.vectorizer = None
            self.lock = threading.RLock()
            
            logger.info(f"✓ SemanticAnalyzer инициализирован (lemmatize: {self.lemmatize}, sklearn: {SKLEARN_AVAILABLE})")
        
        except Exception as e:
            logger.error(f"✗ Ошибка инициализации SemanticAnalyzer: {e}")
            self.lemmatize = False
            self.morph = None
    
    def _lemmatize_text(self, text: str) -> str:
        """Лемматизировать текст"""
        try:
            if not self.lemmatize or not self.morph:
                return text
            
            words = text.split()
            lemmas = []
            
            for word in words:
                try:
                    parsed = self.morph.parse(word)[0]
                    lemma = parsed.normal_form
                    lemmas.append(lemma)
                except Exception:
                    lemmas.append(word)
            
            return ' '.join(lemmas)
        
        except Exception as e:
            logger.debug(f"⚠ Ошибка лемматизации: {e}")
            return text
    
    def analyze(self, keywords: Dict[str, KeywordData], 
                threshold: float = 0.5, 
                n_clusters: int = 10,
                clustering_mode: str = 'threshold') -> Dict[str, List[str]]:
        """
        Кластеризировать ключевые слова
        
        Args:
            keywords: Словарь ключевых слов
            threshold: Порог сходства (для threshold режима)
            n_clusters: Количество кластеров (для fixed режима)
            clustering_mode: 'threshold' или 'fixed'
        
        Returns:
            Словарь кластеров {центр: [ключевые слова]}
        """
        try:
            if not keywords:
                logger.warning("⚠ Пусто ключевых слов для анализа")
                return {}
            
            if not SKLEARN_AVAILABLE:
                logger.warning("⚠ scikit-learn не доступен, возвращаю исходные ключи")
                return {'основной': list(keywords.keys())}
            
            logger.info(f"🤖 Начинаю анализ: {len(keywords)} ключевых слов")
            logger.info(f"   Mode: {clustering_mode}, threshold: {threshold}, clusters: {n_clusters}")
            
            with self.lock:
                # ✅ ПОДГОТОВИТЬ ТЕКСТ
                phrases = list(keywords.keys())
                
                logger.info(f"📝 Обрабатываю {len(phrases)} фраз...")
                
                if self.lemmatize:
                    processed_phrases = [self._lemmatize_text(p) for p in phrases]
                else:
                    processed_phrases = phrases
                
                logger.info(f"✓ Фразы обработаны")
                
                # ✅ СОЗДАТЬ TF-IDF МАТРИЦУ
                logger.info(f"🔢 Создаю TF-IDF матрицу...")
                
                vectorizer = TfidfVectorizer(
                    max_features=self.max_features,
                    ngram_range=(1, 2),
                    lowercase=True,
                    strip_accents='unicode'
                )
                
                tfidf_matrix = vectorizer.fit_transform(processed_phrases)
                logger.info(f"✓ TF-IDF матрица создана: {tfidf_matrix.shape}")
                
                # ✅ ВЫЧИСЛИТЬ СХОДСТВО
                logger.info(f"📊 Вычисляю сходство...")
                similarity_matrix = cosine_similarity(tfidf_matrix)
                logger.info(f"✓ Матрица сходства вычислена")
                
                # ✅ КЛАСТЕРИЗАЦИЯ
                if clustering_mode == 'threshold':
                    clusters = self._cluster_threshold(phrases, similarity_matrix, threshold)
                else:
                    clusters = self._cluster_kmeans(phrases, tfidf_matrix, n_clusters)
                
                logger.info(f"✓ Кластеризация завершена: {len(clusters)} кластеров")
                
                return clusters
        
        except Exception as e:
            logger.error(f"✗ Ошибка анализа: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _cluster_threshold(self, phrases: List[str], 
                          similarity_matrix: np.ndarray,
                          threshold: float = 0.5) -> Dict[str, List[str]]:
        """Кластеризация по порогу сходства"""
        try:
            logger.info(f"🔗 Кластеризация по порогу: {threshold}")
            
            clusters = {}
            assigned = set()
            
            for i, phrase in enumerate(phrases):
                if i in assigned:
                    continue
                
                # ✅ НАЙТИ ВСЕ ПОХОЖИЕ ФРАЗЫ
                similar = [i]
                for j in range(i + 1, len(phrases)):
                    if j not in assigned and similarity_matrix[i, j] >= threshold:
                        similar.append(j)
                        assigned.add(j)
                
                assigned.add(i)
                
                # ✅ ИСПОЛЬЗОВАТЬ САМУЮ ПОПУЛЯРНУЮ КАК ЦЕНТР
                center_phrase = phrase
                cluster_phrases = [phrases[idx] for idx in similar]
                clusters[center_phrase] = cluster_phrases
                
                logger.debug(f"   Кластер '{center_phrase}': {len(cluster_phrases)} фраз")
            
            return clusters
        
        except Exception as e:
            logger.error(f"✗ Ошибка _cluster_threshold: {e}")
            return {}
    
    def _cluster_kmeans(self, phrases: List[str],
                       tfidf_matrix: np.ndarray,
                       n_clusters: int) -> Dict[str, List[str]]:
        """Кластеризация K-Means"""
        try:
            logger.info(f"🎯 Кластеризация K-Means: {n_clusters} кластеров")
            
            # ✅ ОГРАНИЧИТЬ КОЛИЧЕСТВО КЛАСТЕРОВ
            n_clusters = min(n_clusters, len(phrases))
            
            if n_clusters < 1:
                n_clusters = 1
            
            # ✅ ЗАПУСТИТЬ K-MEANS
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(tfidf_matrix)
            
            # ✅ СОБРАТЬ КЛАСТЕРЫ
            clusters = defaultdict(list)
            
            for phrase, label in zip(phrases, labels):
                clusters[label].append(phrase)
            
            # ✅ НАЙТИ ЦЕНТРЫ КЛАСТЕРОВ
            result_clusters = {}
            
            for cluster_id, cluster_phrases in clusters.items():
                # Использовать первую фразу как название
                center_phrase = cluster_phrases[0]
                result_clusters[center_phrase] = cluster_phrases
                
                logger.debug(f"   Кластер {cluster_id} '{center_phrase}': {len(cluster_phrases)} фраз")
            
            return result_clusters
        
        except Exception as e:
            logger.error(f"✗ Ошибка _cluster_kmeans: {e}")
            return {}
    
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
            output.append("РЕЗУЛЬТАТЫ КЛАСТЕРИЗАЦИИ")
            output.append("=" * 80)
            
            for idx, (center, phrases) in enumerate(clusters.items(), 1):
                output.append(f"\n🎯 Кластер {idx}: '{center}'")
                output.append(f"   📊 Размер: {len(phrases)} фраз")
                output.append(f"   📋 Фразы:")
                
                for phrase in phrases[:10]:  # Показать первые 10
                    output.append(f"      • {phrase}")
                
                if len(phrases) > 10:
                    output.append(f"      ... и ещё {len(phrases) - 10} фраз")
            
            output.append("\n" + "=" * 80)
            
            return "\n".join(output)
        
        except Exception as e:
            logger.error(f"✗ Ошибка format_clusters: {e}")
            return str(clusters)