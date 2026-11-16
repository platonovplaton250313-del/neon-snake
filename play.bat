@echo off
setlocal
cd /d "%~dp0"
title NEON SNAKE
echo ==================================
echo             NEON SNAKE
echo ==================================
echo.

py -3 -c "import sys" >nul 2>nul
if not errorlevel 1 goto run_py
python -c "import sys" >nul 2>nul
if not errorlevel 1 goto run_python

echo [ERROR] Python 3 not found in PATH.
echo.
echo Install Python 3.8+ from https://www.python.org/ and enable
echo "Add Python to PATH" during setup, then run this file again.
echo.
pause
exit /b 1

:run_py
py -3 neon_snake.py
set CODE=%errorlevel%
goto finish

:run_python
python neon_snake.py
set CODE=%errorlevel%
goto finish

:finish
if not "%CODE%"=="0" (
    echo.
    echo [NEON SNAKE] Game exited with code %CODE%.
    pause
)
exit /b %CODE%
