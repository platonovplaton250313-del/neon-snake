@echo off
rem Removes this folder from the user PATH.
setlocal
chcp 65001 >nul 2>nul
cd /d "%~dp0"
set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0path_tool.ps1" remove -Dir "%HERE%"
if errorlevel 1 (
    echo.
    echo [brawl] Could not update PATH automatically.
    pause
    exit /b 1
)

echo.
echo Removed. Open a new cmd window for the change to take effect.
pause
