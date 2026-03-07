"""
Генератор промптов для ИИ-редактора из AI-кластеров
"""
import os
import glob
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from utils.logger import get_logger
from storage.models import KeywordData

logger = get_logger('WordStat.ContentBrief')

# Путь к шаблону по умолчанию (относительно корня проекта)
_DEFAULT_TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'prompt', 'template.md'
)
_DEFAULT_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'prompt', 'base'
)


class ContentBriefGenerator:
    """Генератор промптов для ИИ-редактора из AI-кластеров"""

    def __init__(self,
                 template_path: str = _DEFAULT_TEMPLATE_PATH,
                 output_dir: str = _DEFAULT_OUTPUT_DIR,
                 max_priority_keywords: int = 8,
                 max_lsi_keywords: int = 30):
        """
        Args:
            template_path: Путь к файлу шаблона prompt/template.md
            output_dir: Директория для сохранения сгенерированных файлов
            max_priority_keywords: Максимум приоритетных ключей (топ по count)
            max_lsi_keywords: Максимум LSI-ключей
        """
        self.template_path = template_path
        self.output_dir = output_dir
        self.max_priority_keywords = max_priority_keywords
        self.max_lsi_keywords = max_lsi_keywords

        logger.info(
            f"✓ ContentBriefGenerator инициализирован "
            f"(template={template_path}, output={output_dir})"
        )

    def generate_all(self,
                     clusters: Dict[str, List[str]],
                     keywords: Dict[str, KeywordData],
                     clustering_method: str = '') -> int:
        """
        Генерировать промпты для всех кластеров.

        Args:
            clusters: Dict {cluster_name: [phrase, ...]}
            keywords: Dict {phrase: KeywordData}
            clustering_method: Название метода кластеризации

        Returns:
            Количество сгенерированных файлов
        """
        if not clusters:
            logger.warning("⚠ Нет кластеров для генерации промптов")
            return 0

        try:
            # Создать директории если нужно
            os.makedirs(self.output_dir, exist_ok=True)

            # Прочитать шаблон
            template_text = self._load_template()

            # Очистить старые файлы .md в output_dir
            self._clean_output_dir()

            # Подготовить данные всех кластеров (отсортированные по трафику)
            clusters_data = []
            for cluster_name, phrases in clusters.items():
                try:
                    main_kw, main_count = self._get_main_keyword(phrases, keywords)
                    total_traffic = sum(
                        keywords[p].count for p in phrases if p in keywords
                    )
                    clusters_data.append({
                        'name': cluster_name,
                        'phrases': phrases,
                        'main_keyword': main_kw,
                        'main_count': main_count,
                        'total_traffic': total_traffic,
                    })
                except Exception as e:
                    logger.error(f"✗ Ошибка подготовки кластера '{cluster_name}': {e}")

            # Сортировать по суммарному трафику (убывание)
            clusters_data.sort(key=lambda d: d['total_traffic'], reverse=True)

            # Генерировать файлы
            generated = 0
            for idx, data in enumerate(clusters_data, start=1):
                try:
                    file_content = self._generate_single(
                        cluster_num=idx,
                        cluster_name=data['name'],
                        phrases=data['phrases'],
                        keywords=keywords,
                        template_text=template_text,
                    )
                    filename = f"cluster_{idx:03d}.md"
                    filepath = os.path.join(self.output_dir, filename)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(file_content)
                    data['file'] = filename
                    generated += 1
                    logger.debug(f"✓ Записан {filename} ({data['main_keyword']})")
                except Exception as e:
                    logger.error(
                        f"✗ Ошибка генерации файла для кластера "
                        f"'{data['name']}': {e}"
                    )

            # Генерировать оглавление
            try:
                index_content = self._generate_index(clusters_data, clustering_method)
                index_path = os.path.join(self.output_dir, '_index.md')
                with open(index_path, 'w', encoding='utf-8') as f:
                    f.write(index_content)
                logger.info(f"✓ Записан _index.md")
            except Exception as e:
                logger.error(f"✗ Ошибка генерации _index.md: {e}")

            logger.info(
                f"✓ Генерация завершена: {generated} промптов в {self.output_dir}"
            )
            return generated

        except Exception as e:
            logger.error(f"✗ Критическая ошибка generate_all: {e}")
            return 0

    def _load_template(self) -> str:
        """Загрузить текст шаблона из файла"""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(
                f"⚠ Файл шаблона не найден: {self.template_path}. "
                f"Используется пустой шаблон."
            )
            return ''
        except Exception as e:
            logger.error(f"✗ Ошибка чтения шаблона: {e}")
            return ''

    def _clean_output_dir(self) -> None:
        """Удалить старые .md файлы из output_dir"""
        try:
            pattern = os.path.join(self.output_dir, '*.md')
            old_files = glob.glob(pattern)
            for f in old_files:
                try:
                    os.remove(f)
                except Exception as e:
                    logger.warning(f"⚠ Не удалось удалить {f}: {e}")
            if old_files:
                logger.info(f"🗑 Удалено {len(old_files)} старых файлов из {self.output_dir}")
        except Exception as e:
            logger.error(f"✗ Ошибка очистки директории: {e}")

    def _generate_single(self,
                         cluster_num: int,
                         cluster_name: str,
                         phrases: List[str],
                         keywords: Dict[str, KeywordData],
                         template_text: str) -> str:
        """Генерировать один файл промпта для одного кластера"""
        main_kw, main_count = self._get_main_keyword(phrases, keywords)
        topic = self._format_topic(main_kw)

        # Отсортированные по count
        sorted_phrases = self._sort_by_count(phrases, keywords)

        # Разбить на приоритетные и LSI
        priority = sorted_phrases[:self.max_priority_keywords]
        lsi_phrases = sorted_phrases[self.max_priority_keywords:
                                     self.max_priority_keywords + self.max_lsi_keywords]

        # Суммарный трафик
        total_traffic = sum(
            keywords[p].count for p in phrases if p in keywords
        )

        # Сформировать нумерованный список приоритетных ключей
        priority_lines = []
        for i, (phrase, count) in enumerate(priority, start=1):
            count_str = str(count) if count >= 0 else '—'
            priority_lines.append(f"{i}. {phrase} — {count_str}")
        priority_block = '\n'.join(priority_lines)

        # Сформировать строку LSI-ключей
        lsi_block = ', '.join(phrase for phrase, _ in lsi_phrases) if lsi_phrases else '—'

        # Блок ЗАДАНИЕ
        assignment_block = (
            f"\n================================\n"
            f"ЗАДАНИЕ\n"
            f"================================\n"
            f"\n"
            f"Тема статьи: {topic}\n"
            f"\n"
            f"Главный ключевой запрос: {main_kw}\n"
            f"\n"
            f"Ключевые слова (по приоритету частотности):\n"
            f"{priority_block}\n"
            f"\n"
            f"Дополнительные LSI-ключи:\n"
            f"{lsi_block}\n"
            f"\n"
            f"Суммарная частотность кластера: {total_traffic} / мес\n"
            f"Количество ключей в кластере: {len(phrases)}\n"
        )

        return template_text + assignment_block

    def _generate_index(self,
                        clusters_data: List[dict],
                        clustering_method: str = '') -> str:
        """Генерировать оглавление _index.md"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        total_articles = len(clusters_data)
        total_traffic = sum(d['total_traffic'] for d in clusters_data)

        lines = [
            f"# Контент-план — сгенерировано {now}",
            f"",
            f"Всего статей: {total_articles}",
            f"Суммарный трафик: {total_traffic} / мес",
            f"Метод кластеризации: {clustering_method or '—'}",
            f"",
            f"| # | Файл | Тема | Главный ключ | Трафик | Ключей |",
            f"|---|---|---|---|---|---|",
        ]

        for idx, data in enumerate(clusters_data, start=1):
            file_name = data.get('file', f"cluster_{idx:03d}.md")
            topic = self._format_topic(data['main_keyword'])
            main_kw = data['main_keyword']
            main_count = data['main_count']
            count_str = str(main_count) if main_count >= 0 else '—'
            traffic = data['total_traffic']
            n_keys = len(data['phrases'])
            lines.append(
                f"| {idx} | {file_name} | {topic} | {main_kw} ({count_str}) "
                f"| {traffic} | {n_keys} |"
            )

        return '\n'.join(lines) + '\n'

    def _get_main_keyword(self,
                          phrases: List[str],
                          keywords: Dict[str, KeywordData]) -> Tuple[str, int]:
        """
        Получить главный ключ (максимальный count).

        Returns:
            Tuple[phrase, count]. count = -1 если не найден в keywords.
        """
        if not phrases:
            return ('', -1)

        first_phrase = phrases[0]
        best_phrase = first_phrase
        best_count = keywords[first_phrase].count if first_phrase in keywords else -1

        for phrase in phrases[1:]:
            if phrase in keywords:
                c = keywords[phrase].count
                if best_count < 0 or c > best_count:
                    best_phrase = phrase
                    best_count = c

        return (best_phrase, best_count)

    def _sort_by_count(self,
                       phrases: List[str],
                       keywords: Dict[str, KeywordData]) -> List[Tuple[str, int]]:
        """
        Отсортировать фразы по count (убывание).

        Returns:
            List of (phrase, count) tuples. count = -1 если не найден.
        """
        result = []
        for phrase in phrases:
            count = keywords[phrase].count if phrase in keywords else -1
            result.append((phrase, count))
        result.sort(key=lambda x: x[1], reverse=True)
        return result

    def _format_topic(self, main_keyword: str) -> str:
        """Сформировать тему статьи из главного ключа (первая буква заглавная)"""
        if not main_keyword:
            return ''
        return main_keyword[0].upper() + main_keyword[1:]
