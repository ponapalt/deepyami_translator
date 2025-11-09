@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo DeepYami翻訳アプリ
echo ========================================
echo.

REM Pythonの存在確認
python --version >nul 2>&1
if errorlevel 1 (
    echo [エラー] Pythonが見つかりません。
    echo Pythonをインストールしてから再度実行してください。
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM venvの存在確認
if not exist "venv\" (
    echo [1/3] 仮想環境を作成しています...
    python -m venv venv
    if errorlevel 1 (
        echo [エラー] 仮想環境の作成に失敗しました。
        pause
        exit /b 1
    )
    echo 仮想環境を作成しました。
    echo.
) else (
    echo [1/3] 仮想環境が見つかりました。
    echo.
)

REM venv有効化
echo [2/3] 仮想環境を有効化しています...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [エラー] 仮想環境の有効化に失敗しました。
    pause
    exit /b 1
)
echo.

REM 依存関係インストール
echo [3/3] 依存関係をインストールしています...
echo これには数分かかる場合があります...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if errorlevel 1 (
    echo [エラー] 依存関係のインストールに失敗しました。
    echo インターネット接続を確認してください。
    pause
    exit /b 1
)
echo 依存関係をインストールしました。
echo.

REM アプリ起動
echo ========================================
echo アプリケーションを起動します...
echo ========================================
echo.
python app.py

if errorlevel 1 (
    echo.
    echo [エラー] アプリケーションの起動に失敗しました。
    pause
    exit /b 1
)

endlocal
