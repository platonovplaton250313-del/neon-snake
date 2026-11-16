@echo off
setlocal
cd /d "%~dp0"
where pythonw >nul 2>nul
if errorlevel 1 goto fallback
start "" pythonw neon_snake.py
exit /b 0

:fallback
call "%~dp0play.bat"
