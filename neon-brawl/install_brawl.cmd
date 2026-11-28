@echo off
rem Adds this folder to the user PATH, so "brawl" works in any new cmd window.
setlocal
chcp 65001 >nul 2>nul
cd /d "%~dp0"
set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"

if not exist "%~dp0neon_brawl.py" (
    echo [brawl] neon_brawl.py not found next to this file.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0path_tool.ps1" add -Dir "%HERE%"
if errorlevel 1 (
    echo.
    echo [brawl] Could not update PATH automatically.
    echo Add this folder to PATH manually:
    echo   %~dp0
    pause
    exit /b 1
)

echo.
echo Done. Open a NEW cmd window and type:
echo.
echo     brawl
echo.
echo Console mode: brawl -c
echo Smoke test:   brawl -smoke
echo.
echo Uninstall with uninstall_brawl.cmd
pause
