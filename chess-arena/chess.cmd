@echo off
rem ============================================================
rem  CHESS ARENA - launch the game from CMD
rem
rem    chess                 start the game and open the browser
rem    chess -Port 8145      use another local port
rem    chess -NoBrowser      start the server only
rem    chess -Check          show what will be launched
rem
rem  Close the server window to stop the game.
rem ============================================================
setlocal EnableExtensions
chcp 65001 >nul 2>nul
title CHESS ARENA - local server
cd /d "%~dp0"

set "PS1=%~dp0serve_chess.ps1"

if not exist "%PS1%" goto no_script

where powershell >nul 2>nul
if errorlevel 1 goto no_powershell

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
set "CODE=%errorlevel%"

if /i "%~1"=="-Check" exit /b %CODE%
if /i "%~1"=="-check" exit /b %CODE%

if not "%CODE%"=="0" (
    echo.
    echo [chess] The server exited with code %CODE%.
    echo [chess] Try: chess -Port 8145
    pause
)

exit /b %CODE%

:no_script
echo.
echo [chess] serve_chess.ps1 was not found next to chess.cmd.
echo [chess] Keep chess.cmd and serve_chess.ps1 in the same folder.
echo.
pause
exit /b 1

:no_powershell
echo.
echo [chess] Windows PowerShell was not found.
echo [chess] It is included with Windows 10 and 11 by default.
echo.
pause
exit /b 1
