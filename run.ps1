# AOI System One-Click PowerShell Launcher
$ErrorActionPreference = "Stop"
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  AOI 智慧尺寸量測與品質判定系統啟動器 (PowerShell) " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[INFO] 正在初始化虛擬環境 (uv)..." -ForegroundColor Yellow
    uv venv
    uv pip install -e ".[test]"
}

Write-Host "[INFO] 啟動 AOI 檢測軟體..." -ForegroundColor Green
& .venv\Scripts\python.exe main.py
