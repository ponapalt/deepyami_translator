@echo off
setlocal enabledelayedexpansion

echo ========================================
echo DeepYami Translation App
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo Please install Python and try again.
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

git pull

if not exist "venv\" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Virtual environment created.
    echo.
) else (
    echo [1/3] Virtual environment found.
    echo.
)

echo [2/3] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)
echo.

echo [3/3] Installing dependencies...
echo This may take a few minutes...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    echo Please check your internet connection.
    pause
    exit /b 1
)
echo Dependencies installed.
echo.

echo ========================================
echo Starting application...
echo ========================================
echo.
python app.py

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start application.
    pause
    exit /b 1
)

endlocal
