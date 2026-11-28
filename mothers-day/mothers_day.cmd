@echo off
rem ============================================================
rem  MOTHERS DAY CARD - launcher
rem    mothers_day.cmd          start without a console window
rem    mothers_day.cmd -c       start with console (shows errors)
rem    mothers_day.cmd -check   show what would be launched
rem ============================================================
setlocal EnableExtensions
set "DIR=%~dp0"
set "GAME=%~dp0mothers_day.py"
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
    echo [mothers-day] launcher : %~f0
    echo [mothers-day] card     : %GAME%
    echo [mothers-day] command  : %WINRUN% "%GAME%"
    %CONRUN% -c "import pygame; print('[mothers-day] pygame  : ' + pygame.version.ver)"
    exit /b 0
)

%CONRUN% -c "import pygame" >nul 2>nul
if errorlevel 1 (
    echo [mothers-day] pygame is not installed.
    echo [mothers-day] Installing pygame-ce. This needs an internet connection...
    %CONRUN% -m pip install --upgrade pygame-ce
    if errorlevel 1 goto no_pygame
)

if /i "%MODE%"=="console" (
    %CONRUN% "%GAME%"
    set "CODE=%errorlevel%"
    if not "%CODE%"=="0" (
        echo.
        echo [mothers-day] The card exited with code %CODE%.
        pause
    )
    exit /b %CODE%
)

start "" %WINRUN% "%GAME%"
if errorlevel 1 goto launch_failed
exit /b 0

:launch_failed
echo [mothers-day] Could not start Python.
echo Run "mothers_day.cmd -c" to see the error message.
pause
exit /b 1

:no_game
echo [mothers-day] Card file not found:
echo   %GAME%
echo Keep mothers_day.cmd next to mothers_day.py.
pause
exit /b 1

:no_python
echo [mothers-day] Python 3 was not found in PATH.
echo.
echo Install Python 3.9+ from https://www.python.org/
echo and tick "Add python.exe to PATH" during setup.
echo Then open a NEW cmd window and run mothers_day.cmd
pause
exit /b 1

:no_pygame
echo.
echo [mothers-day] Could not install pygame-ce.
echo Try manually:  python -m pip install pygame-ce
pause
exit /b 1
