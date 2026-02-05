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

# Русские стоп-слова для фильтрации
RUSSIAN_STOP_WORDS = {
    'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все',
    'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по',
    'только', 'её', 'мне', 'было', 'вот', 'от', 'меня', 'ещё', 'нет', 'о', 'из', 'ему',
    'теперь', 'когда', 'уже', 'для', 'вас', 'нибудь', 'был', 'чего', 'тут', 'здесь',
    'если', 'их', 'или', 'ни', 'быть', 'при', 'чем', 'без', 'до', 'под', 'над', 'об'
}


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
            self._last_clusters = {}  # Хранение последних результатов
            
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
            self._last_clusters = {}
    
    def _lemmatize_text(self, text: str, remove_stop_words: bool = True) -> str:
        """Лемматизировать текст и удалить стоп-слова"""
        try:
            words = text.lower().split()
            result_words = []
            
            for word in words:
                # Удалить стоп-слова
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
    
    def analyze(self, keywords: Dict[str, KeywordData], 
                threshold: float = 0.5, 
                n_clusters: int = 10,
                clustering_mode: str = 'threshold',
                min_cluster_size: int = 2) -> Dict[str, List[str]]:
        """
        Кластеризировать ключевые слова
        
        Args:
            keywords: Словарь ключевых слов
            threshold: Порог сходства (для threshold режима)
            n_clusters: Количество кластеров (для fixed режима)
            clustering_mode: 'threshold' или 'fixed'
            min_cluster_size: Минимальный размер кластера (по умолчанию 2)
        
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
                
                processed_phrases = [self._lemmatize_text(p) for p in phrases]
                
                # Фильтруем пустые обработанные фразы
                valid_indices = [i for i, p in enumerate(processed_phrases) if p.strip()]
                if len(valid_indices) < len(phrases):
                    logger.info(f"⚠ Отфильтровано {len(phrases) - len(valid_indices)} пустых фраз")
                    phrases = [phrases[i] for i in valid_indices]
                    processed_phrases = [processed_phrases[i] for i in valid_indices]
                
                if len(phrases) < 2:
                    logger.warning("⚠ Недостаточно фраз для кластеризации")
                    return {'Другое': phrases} if phrases else {}
                
                logger.info(f"✓ Фразы обработаны")
                
                # ✅ СОЗДАТЬ TF-IDF МАТРИЦУ с улучшенными параметрами
                logger.info(f"🔢 Создаю TF-IDF матрицу...")
                
                vectorizer = TfidfVectorizer(
                    max_features=self.max_features,
                    ngram_range=(1, 3),  # Улучшено: добавлены триграммы для лучшего сходства
                    lowercase=True,
                    strip_accents='unicode',
                    min_df=1,
                    max_df=0.95,  # Игнорируем слишком частые термины
                    sublinear_tf=True  # Лучше для длинных документов
                )
                
                tfidf_matrix = vectorizer.fit_transform(processed_phrases)
                logger.info(f"✓ TF-IDF матрица создана: {tfidf_matrix.shape}")
                
                # ✅ ВЫЧИСЛИТЬ СХОДСТВО
                logger.info(f"📊 Вычисляю сходство...")
                similarity_matrix = cosine_similarity(tfidf_matrix)
                logger.info(f"✓ Матрица сходства вычислена")
                
                # ✅ КЛАСТЕРИЗАЦИЯ
                if clustering_mode == 'fixed':
                    clusters = self._cluster_agglomerative(phrases, tfidf_matrix, n_clusters)
                else:
                    clusters = self._cluster_threshold(phrases, similarity_matrix, threshold)
                
                # ✅ ПРИМЕНИТЬ МИНИМАЛЬНЫЙ РАЗМЕР КЛАСТЕРА
                clusters = self._enforce_min_cluster_size(clusters, min_cluster_size)
                
                logger.info(f"✓ Кластеризация завершена: {len(clusters)} кластеров")
                
                # Сохраним последние результаты для экспорта
                self._last_clusters = clusters
                
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
    
    def _cluster_agglomerative(self, phrases: List[str],
                               tfidf_matrix,
                               n_clusters: int) -> Dict[str, List[str]]:
        """Кластеризация Agglomerative - лучше для семантических групп"""
        try:
            logger.info(f"🎯 Кластеризация Agglomerative: {n_clusters} кластеров")
            
            # ✅ ОГРАНИЧИТЬ КОЛИЧЕСТВО КЛАСТЕРОВ
            # Убедимся, что n_clusters не больше количества фраз
            actual_n_clusters = min(n_clusters, len(phrases))
            
            # Минимум 1 кластер
            if actual_n_clusters < 1:
                actual_n_clusters = 1
            
            logger.info(f"   Используем {actual_n_clusters} кластеров (запрошено: {n_clusters}, фраз: {len(phrases)})")
            
            # ✅ ИСПОЛЬЗОВАТЬ AGGLOMERATIVE CLUSTERING
            # Он лучше группирует семантически похожие слова
            clustering = AgglomerativeClustering(
                n_clusters=actual_n_clusters,
                metric='euclidean',
                linkage='ward'
            )
            
            # Преобразуем sparse matrix в dense для AgglomerativeClustering
            dense_matrix = tfidf_matrix.toarray()
            labels = clustering.fit_predict(dense_matrix)
            
            # ✅ СОБРАТЬ КЛАСТЕРЫ
            clusters = defaultdict(list)
            
            for phrase, label in zip(phrases, labels):
                clusters[label].append(phrase)
            
            # ✅ НАЙТИ ЦЕНТРЫ КЛАСТЕРОВ (первая фраза как название)
            result_clusters = {}
            
            for cluster_id, cluster_phrases in clusters.items():
                # Использовать первую фразу как название
                center_phrase = cluster_phrases[0]
                result_clusters[center_phrase] = cluster_phrases
                
                logger.debug(f"   Кластер {cluster_id} '{center_phrase}': {len(cluster_phrases)} фраз")
            
            return result_clusters
        
        except Exception as e:
            logger.error(f"✗ Ошибка _cluster_agglomerative: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to simple grouping
            return {'Другое': phrases}
    
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
            other_phrases = []
            
            for center, phrases in clusters.items():
                if len(phrases) >= min_size:
                    result[center] = phrases
                else:
                    # Добавляем в "Другое"
                    other_phrases.extend(phrases)
                    logger.debug(f"   Кластер '{center}' ({len(phrases)} фраз) -> Другое")
            
            # Добавляем кластер "Другое" если есть некластеризованные
            if other_phrases:
                result['Другое'] = other_phrases
                logger.info(f"   📦 Кластер 'Другое': {len(other_phrases)} фраз")
            
            logger.info(f"✓ После фильтрации: {len(result)} кластеров")
            return result
        
        except Exception as e:
            logger.error(f"✗ Ошибка _enforce_min_cluster_size: {e}")
            return clusters
    
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
    
    def format_clusters_for_export(self, clusters: Dict[str, List[str]]) -> str:
        """Форматировать кластеры для экспорта (полный список)"""
        try:
            if not clusters:
                return "Кластеры не найдены"
            
            output = []
            output.append("РЕЗУЛЬТАТЫ AI КЛАСТЕРИЗАЦИИ")
            output.append("=" * 80)
            output.append("")
            
            for idx, (center, phrases) in enumerate(clusters.items(), 1):
                output.append(f"КЛАСТЕР {idx}: {center}")
                output.append(f"Количество: {len(phrases)}")
                output.append("-" * 40)
                
                for phrase in phrases:  # Все фразы
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