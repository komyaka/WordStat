#!/usr/bin/env python3
"""
SEO Wordstat Master AI v.2026
Точка входа приложения
"""
import sys
import os, site

for sp in site.getsitepackages():
    candidate = os.path.join(sp, "torch", "lib")
    if os.path.isdir(candidate):
        os.add_dll_directory(candidate)
        break

# ВАЖНО: прогреваем torch до любых GUI/прочих импортов
import torch

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
