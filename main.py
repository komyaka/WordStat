#!/usr/bin/env python3
"""
SEO Wordstat Master AI v.2026
Точка входа приложения
"""
import sys
import os

# Добавить текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import main

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹ Приложение остановлено пользователем")
    except Exception as e:
        print(f"\n✗ Критическая ошибка: {e}")
        sys.exit(1)