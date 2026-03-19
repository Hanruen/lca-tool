@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo =========================================
echo  工程材料碳足跡計算工具
echo =========================================
echo.

:: 嘗試找到 Python（依序試 python / py / python3）
set PYTHON_CMD=

python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
    goto :found_python
)

py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py
    goto :found_python
)

python3 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python3
    goto :found_python
)

echo [錯誤] 找不到 Python，請先安裝 Python 3
echo 下載網址：https://www.python.org
echo 安裝時請勾選「Add Python to PATH」
echo.
pause
exit /b 1

:found_python
echo 使用 Python 指令：%PYTHON_CMD%
%PYTHON_CMD% --version
echo.

:: 第一次執行時安裝套件
if not exist ".installed" (
    echo 首次執行，安裝必要套件（約需 1-2 分鐘）...
    echo.
    %PYTHON_CMD% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [錯誤] 套件安裝失敗，請確認網路連線後再試一次。
        pause
        exit /b 1
    )
    echo. > .installed
    echo.
    echo 套件安裝完成！
    echo.
)

echo 啟動中，請稍候...
echo 瀏覽器將自動開啟，若未自動開啟請手動前往：http://localhost:8501
echo （關閉此視窗即可停止程式）
echo.

%PYTHON_CMD% -m streamlit run app.py --server.headless true --browser.gatherUsageStats false --server.port 8501

echo.
echo 程式已停止。
pause
