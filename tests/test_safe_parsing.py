"""
Тест безопасного парсинга числовых параметров
"""
import sys
import os

# Добавить родительскую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.main_window import _safe_int, _safe_float


def test_safe_int():
    """Тест _safe_int"""
    print("=" * 80)
    print("TEST: _safe_int")
    print("=" * 80)
    
    # Тест 1: Нормальное значение
    result = _safe_int("5", default=1)
    assert result == 5, f"Expected 5, got {result}"
    print("✓ Нормальное значение: '5' -> 5")
    
    # Тест 2: Пустая строка
    result = _safe_int("", default=1)
    assert result == 1, f"Expected 1, got {result}"
    print("✓ Пустая строка: '' -> 1 (default)")
    
    # Тест 3: None
    result = _safe_int(None, default=1)
    assert result == 1, f"Expected 1, got {result}"
    print("✓ None -> 1 (default)")
    
    # Тест 4: Невалидная строка
    result = _safe_int("abc", default=1)
    assert result == 1, f"Expected 1, got {result}"
    print("✓ Невалидная строка: 'abc' -> 1 (default)")
    
    # Тест 5: Значение меньше min
    result = _safe_int("0", default=1, min_val=1)
    assert result == 1, f"Expected 1, got {result}"
    print("✓ Значение меньше min: '0' с min_val=1 -> 1 (clamped)")
    
    # Тест 6: Значение больше max
    result = _safe_int("200", default=10, max_val=100)
    assert result == 100, f"Expected 100, got {result}"
    print("✓ Значение больше max: '200' с max_val=100 -> 100 (clamped)")
    
    # Тест 7: Значение в диапазоне
    result = _safe_int("50", default=10, min_val=1, max_val=100)
    assert result == 50, f"Expected 50, got {result}"
    print("✓ Значение в диапазоне: '50' с min=1, max=100 -> 50")
    
    # Тест 8: Отрицательное число
    result = _safe_int("-5", default=1, min_val=1)
    assert result == 1, f"Expected 1, got {result}"
    print("✓ Отрицательное число: '-5' с min_val=1 -> 1 (clamped)")
    
    print()


def test_safe_float():
    """Тест _safe_float"""
    print("=" * 80)
    print("TEST: _safe_float")
    print("=" * 80)
    
    # Тест 1: Нормальное значение
    result = _safe_float("0.5", default=0.0)
    assert result == 0.5, f"Expected 0.5, got {result}"
    print("✓ Нормальное значение: '0.5' -> 0.5")
    
    # Тест 2: Пустая строка
    result = _safe_float("", default=0.5)
    assert result == 0.5, f"Expected 0.5, got {result}"
    print("✓ Пустая строка: '' -> 0.5 (default)")
    
    # Тест 3: None
    result = _safe_float(None, default=0.5)
    assert result == 0.5, f"Expected 0.5, got {result}"
    print("✓ None -> 0.5 (default)")
    
    # Тест 4: Невалидная строка
    result = _safe_float("abc", default=0.5)
    assert result == 0.5, f"Expected 0.5, got {result}"
    print("✓ Невалидная строка: 'abc' -> 0.5 (default)")
    
    # Тест 5: Значение меньше min
    result = _safe_float("-0.1", default=0.5, min_val=0.0)
    assert result == 0.0, f"Expected 0.0, got {result}"
    print("✓ Значение меньше min: '-0.1' с min_val=0.0 -> 0.0 (clamped)")
    
    # Тест 6: Значение больше max
    result = _safe_float("1.5", default=0.5, max_val=1.0)
    assert result == 1.0, f"Expected 1.0, got {result}"
    print("✓ Значение больше max: '1.5' с max_val=1.0 -> 1.0 (clamped)")
    
    # Тест 7: Значение в диапазоне
    result = _safe_float("0.7", default=0.5, min_val=0.0, max_val=1.0)
    assert result == 0.7, f"Expected 0.7, got {result}"
    print("✓ Значение в диапазоне: '0.7' с min=0.0, max=1.0 -> 0.7")
    
    # Тест 8: Целое число как float
    result = _safe_float("1", default=0.5, min_val=0.0, max_val=1.0)
    assert result == 1.0, f"Expected 1.0, got {result}"
    print("✓ Целое число: '1' -> 1.0")
    
    print()


def main():
    """Запуск всех тестов"""
    print()
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ БЕЗОПАСНОГО ПАРСИНГА ПАРАМЕТРОВ")
    print("=" * 80)
    print()
    
    try:
        test_safe_int()
        test_safe_float()
        
        print("=" * 80)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
        print("=" * 80)
        print()
        return 0
        
    except AssertionError as e:
        print()
        print("=" * 80)
        print(f"❌ ТЕСТ ПРОВАЛЕН: {e}")
        print("=" * 80)
        print()
        return 1
    
    except Exception as e:
        print()
        print("=" * 80)
        print(f"❌ ОШИБКА: {e}")
        print("=" * 80)
        print()
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
