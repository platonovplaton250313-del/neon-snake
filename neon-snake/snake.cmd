@echo off
rem ============================================================
rem  NEON SNAKE - run the game with a single word:  snake
rem  Options:
rem    snake            start the game (no console window)
rem    snake -c         start with console (shows errors)
rem    snake -check     print what would be launched, do not run
rem ============================================================
setlocal EnableExtensions
set "DIR=%~dp0"
set "GAME=%~dp0neon_snake.py"
set "MODE=quiet"

if /i "%~1"=="-check" set "MODE=check"
if /i "%~1"=="-c" set "MODE=console"
if /i "%~1"=="-console" set "MODE=console"

if not exist "%GAME%" goto no_game

where pyw >nul 2>nul
if not errorlevel 1 goto have_pyw
where pythonw >nul 2>nul
if not errorlevel 1 goto have_pythonw
where py >nul 2>nul
if not errorlevel 1 goto have_py
where python >nul 2>nul
if not errorlevel 1 goto have_python
goto no_python

:have_pyw
set "WINRUN=pyw -3"
set "CONRUN=py -3"
goto launch

:have_pythonw
set "WINRUN=pythonw"
set "CONRUN=python"
goto launch

:have_py
set "WINRUN=py -3"
set "CONRUN=py -3"
goto launch

:have_python
set "WINRUN=python"
set "CONRUN=python"
goto launch

:launch
if /i "%MODE%"=="check" (
    echo [snake] launcher : %~f0
    echo [snake] game     : %GAME%
    echo [snake] command  : %WINRUN% "%GAME%"
    exit /b 0
)
if /i "%MODE%"=="console" (
    %CONRUN% "%GAME%"
    set "CODE=%errorlevel%"
    if not "%CODE%"=="0" (
        echo.
        echo [snake] Game exited with code %CODE%.
        pause
    )
    exit /b %CODE%
)

start "" %WINRUN% "%GAME%"
if errorlevel 1 goto launch_failed
exit /b 0

:launch_failed
echo [snake] Could not start Python.
echo Type "snake -c" to see the error message.
if not "%MODE%"=="check" pause
exit /b 1

:no_game
echo [snake] Game file not found:
echo   %GAME%
echo Keep snake.cmd next to neon_snake.py.
if not "%MODE%"=="check" pause
exit /b 1

:no_python
echo [snake] Python 3 was not found in PATH.
echo.
echo Install Python 3.8+ from https://www.python.org/
echo and tick "Add python.exe to PATH" during setup.
echo Then open a NEW cmd window and type: snake
if not "%MODE%"=="check" pause
exit /b 1
