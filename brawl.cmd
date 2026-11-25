@echo off
rem ============================================================
rem  NEON BRAWL - launch the game from CMD
rem
rem    brawl            start the game (no console window)
rem    brawl -c         start with console (shows errors)
rem    brawl -smoke     run the built-in smoke test
rem    brawl -check     print what would be launched
rem
rem  Run install_brawl.cmd once to use "brawl" in any folder.
rem ============================================================
setlocal EnableExtensions
chcp 65001 >nul 2>nul
set "GAME=%~dp0neon_brawl.py"
set "MODE=quiet"

if /i "%~1"=="-check" set "MODE=check"
if /i "%~1"=="-c" set "MODE=console"
if /i "%~1"=="-console" set "MODE=console"
if /i "%~1"=="-smoke" set "MODE=smoke"
if /i "%~1"=="--smoke" set "MODE=smoke"

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
if /i "%MODE%"=="check" goto check
if /i "%MODE%"=="smoke" goto smoke
if /i "%MODE%"=="console" goto console
goto quiet

:check
echo [brawl] launcher : %~f0
echo [brawl] game     : %GAME%
echo [brawl] command  : %WINRUN% "%GAME%"
echo [brawl] smoke    : %CONRUN% "%GAME%" --smoke
exit /b 0

:smoke
%CONRUN% "%GAME%" --smoke
set "CODE=%errorlevel%"
if not "%CODE%"=="0" (
    echo.
    echo [brawl] Smoke test failed with code %CODE%.
    pause
)
exit /b %CODE%

:console
%CONRUN% "%GAME%"
set "CODE=%errorlevel%"
if not "%CODE%"=="0" (
    echo.
    echo [brawl] Game exited with code %CODE%.
    pause
)
exit /b %CODE%

:quiet
start "" %WINRUN% "%GAME%"
if errorlevel 1 goto launch_failed
exit /b 0

:launch_failed
echo [brawl] Could not start Python.
echo Type "brawl -c" to see the error message.
pause
exit /b 1

:no_game
echo [brawl] Game file not found:
echo   %GAME%
pause
exit /b 1

:no_python
echo [brawl] Python 3 was not found in PATH.
echo Install Python 3.8+ from https://www.python.org/
echo and enable "Add Python to PATH" during setup.
pause
exit /b 1
