@echo off
rem Adds this folder to the user PATH, so "snake" works in any new cmd window.
setlocal
cd /d "%~dp0"
set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"

if not exist "%~dp0neon_snake.py" (
    echo [snake] neon_snake.py not found next to this file.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0path_tool.ps1" add -Dir "%HERE%"
if errorlevel 1 (
    echo.
    echo [snake] Could not update PATH automatically.
    echo Add this folder to PATH manually:
    echo   %~dp0
    pause
    exit /b 1
)

echo.
echo Done. Open a NEW cmd window and type:
echo.
echo     snake
echo.
echo Uninstall with uninstall_snake.cmd
pause
