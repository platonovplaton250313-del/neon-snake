@echo off
rem Removes this folder from the user PATH.
setlocal
cd /d "%~dp0"
set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0path_tool.ps1" remove -Dir "%HERE%"
if errorlevel 1 (
    echo.
    echo [snake] Could not update PATH automatically.
    pause
    exit /b 1
)

echo.
echo Removed. Open a new cmd window for the change to take effect.
pause
