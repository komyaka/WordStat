"""
Проверка синтаксиса всех Python файлов
"""
import py_compile
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_syntax(directory: str) -> tuple:
    """Проверить синтаксис всех Python файлов"""
    errors = []
    checked = 0
    
    for root, dirs, files in os.walk(directory):
        # Пропустить __pycache__ и .git
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'venv']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    py_compile.compile(filepath, doraise=True)
                    print(f"✓ {filepath}")
                    checked += 1
                except py_compile.PyCompileError as e:
                    print(f"✗ {filepath}: {e}")
                    errors.append((filepath, str(e)))
    
    return checked, errors

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    checked, errors = check_syntax(base_dir)
    
    print(f"\n{'='*80}")
    print(f"Проверено файлов: {checked}")
    print(f"Ошибок синтаксиса: {len(errors)}")
    print(f"{'='*80}\n")
    
    if errors:
        print("ОШИБКИ:")
        for filepath, error in errors:
            print(f"  {filepath}: {error}")
        sys.exit(1)
    else:
        print("✅ ВСЕ ФАЙЛЫ СИНТАКСИЧЕСКИ КОРРЕКТНЫ")