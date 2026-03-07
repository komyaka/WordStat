@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ============================================
echo   SEO Wordstat Master AI - Запуск (Windows)
echo ============================================
echo.

:: ─── Проверка Python ────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден в PATH.
    echo Скачайте и установите Python 3.10+ с https://www.python.org/downloads/
    echo При установке обязательно поставьте галочку "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v
echo [OK] Обнаружен: %PYTHON_VERSION%

:: ─── Проверка версии Python (минимум 3.10) ──────────────────────────────────
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
for /f "tokens=1,2 delims=." %%a in ("!PY_VER!") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)
if !PY_MAJOR! LSS 3 (
    echo [ОШИБКА] Требуется Python 3.10 или новее. Установлен: !PY_VER!
    pause
    exit /b 1
)
if !PY_MAJOR! EQU 3 if !PY_MINOR! LSS 10 (
    echo [ОШИБКА] Требуется Python 3.10 или новее. Установлен: !PY_VER!
    pause
    exit /b 1
)

:: ─── Проверка pip ────────────────────────────────────────────────────────────
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] pip не найден. Попытка установить pip автоматически...
    python -m ensurepip --upgrade
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось установить pip автоматически.
        echo Выполните вручную: python -m ensurepip --upgrade
        pause
        exit /b 1
    )
)
for /f "tokens=*" %%v in ('python -m pip --version 2^>^&1') do set PIP_VERSION=%%v
echo [OK] Обнаружен: %PIP_VERSION%

:: ─── Проверка наличия requirements.txt ─────────────────────────────────────
if not exist "%~dp0requirements.txt" (
    echo [ОШИБКА] Файл requirements.txt не найден рядом со скриптом.
    pause
    exit /b 1
)

:: ─── Установка отсутствующих зависимостей ───────────────────────────────────
echo.
echo Проверка зависимостей из requirements.txt...
python -m pip install -r "%~dp0requirements.txt" --quiet --no-warn-script-location
if errorlevel 1 (
    echo [ПРЕДУПРЕЖДЕНИЕ] Часть пакетов не удалось установить тихо; повтор с выводом...
    python -m pip install -r "%~dp0requirements.txt" --no-warn-script-location
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось установить все зависимости.
        echo Проверьте подключение к интернету или запустите от имени администратора.
        pause
        exit /b 1
    )
)
echo [OK] Все зависимости установлены.

:: ─── Запуск приложения ───────────────────────────────────────────────────────
echo.
echo Запуск приложения...
echo.

cd /d "%~dp0"
python main.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Приложение завершилось с ошибкой (код: %errorlevel%).
    pause
    exit /b %errorlevel%
)

endlocal
