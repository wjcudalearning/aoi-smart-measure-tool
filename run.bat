@echo off
chcp 65001 > nul
echo ===================================================
echo   AOI 智慧尺寸量測與品質判定系統啟動器 (Launcher)
echo ===================================================

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] 正在建立虛擬環境並安裝相依套件...
    uv venv
    uv pip install -e ".[test]"
)

echo [INFO] 啟動 AOI 檢測主程式...
.venv\Scripts\python.exe main.py
if errorlevel 1 (
    echo [ERROR] 程式異常退出，請檢查 logs\ 目錄。
    pause
)
