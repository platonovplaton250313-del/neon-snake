@echo off
rem ============================================================
rem  CHESS ARENA - install for the current Windows user
rem
rem  Copy the game to:
rem    %LOCALAPPDATA%\ChessArena
rem
rem  Then add that folder to the user PATH, so a NEW cmd window
rem  can start the game with one word:
rem
rem    chess
rem
rem  Usage:
rem    install_chess.cmd                 normal install
rem    install_chess.cmd D:\Games\Chess  install to another folder
rem    install_chess.cmd --no-path       do not change PATH
rem ============================================================
setlocal EnableExtensions
chcp 65001 >nul 2>nul
cd /d "%~dp0"

if not defined LOCALAPPDATA set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"

set "TARGET=%LOCALAPPDATA%\ChessArena"
set "ADD_PATH=1"

if not "%~1"=="" (
    if /i "%~1"=="--no-path" (
        set "ADD_PATH=0"
    ) else (
        set "TARGET=%~1"
    )
)
if /i "%~2"=="--no-path" set "ADD_PATH=0"
if "%TARGET:~-1%"=="\" set "TARGET=%TARGET:~0,-1%"

rem ---------- locate the game files ----------
set "SRC="
if exist "%~dp0docs\chess\index.html" set "SRC=%~dp0docs"
if not defined SRC if exist "%~dp0..\docs\chess\index.html" set "SRC=%~dp0..\docs"
if not defined SRC if exist "%~dp0app\chess\index.html" set "SRC=%~dp0app"
if not defined SRC if exist "%~dp0chess\index.html" set "SRC=%~dp0"
if not defined SRC if exist "%~dp0index.html" set "SRC=%~dp0"

if not defined SRC goto no_source
if not exist "%SRC%\chess\index.html" goto no_source
if not exist "%~dp0serve_chess.ps1" goto no_launcher

where powershell >nul 2>nul
if errorlevel 1 goto no_powershell

echo.
echo  CHESS ARENA - installation
echo  --------------------------
echo  Source : %SRC%
echo  Target : %TARGET%
echo.

if not exist "%TARGET%" mkdir "%TARGET%" >nul 2>nul
if errorlevel 1 goto no_write

if not exist "%TARGET%\app" mkdir "%TARGET%\app" >nul 2>nul
if errorlevel 1 goto no_write

rem ---------- copy the game ----------
set "COPY_APP=1"
if /i "%SRC%\chess"=="%TARGET%\app\chess" set "COPY_APP=0"

if "%COPY_APP%"=="1" (
    echo  Copying game files...
    xcopy "%SRC%\chess" "%TARGET%\app\chess\" /E /I /Y /Q >nul
    if errorlevel 2 goto copy_failed

    if exist "%SRC%\icons" (
        xcopy "%SRC%\icons" "%TARGET%\app\icons\" /E /I /Y /Q >nul
        if errorlevel 2 goto copy_failed
    )
) else (
    echo  Game files are already in place.
)

if /i not "%~dp0"=="%TARGET%\" (
    copy /Y "%~dp0serve_chess.ps1" "%TARGET%\serve_chess.ps1" >nul 2>nul
    if errorlevel 1 goto copy_failed
    copy /Y "%~dp0chess.cmd" "%TARGET%\chess.cmd" >nul 2>nul
    if errorlevel 1 goto copy_failed
    if exist "%~dp0uninstall_chess.cmd" copy /Y "%~dp0uninstall_chess.cmd" "%TARGET%\uninstall_chess.cmd" >nul 2>nul
    if exist "%~dp0path_tool.ps1" copy /Y "%~dp0path_tool.ps1" "%TARGET%\path_tool.ps1" >nul 2>nul
)

if not exist "%TARGET%\serve_chess.ps1" goto copy_failed
if not exist "%TARGET%\chess.cmd" goto copy_failed

rem ---------- add to PATH ----------
set "PATH_FAILED="
if "%ADD_PATH%"=="1" (
    echo  Adding the launcher to PATH...
    if exist "%TARGET%\path_tool.ps1" (
        powershell -NoProfile -ExecutionPolicy Bypass -File "%TARGET%\path_tool.ps1" add -Dir "%TARGET%"
        if errorlevel 1 set "PATH_FAILED=1"
    ) else (
        set "PATH_FAILED=1"
    )
)

echo.
echo  Done. CHESS ARENA is installed.
echo.
if defined PATH_FAILED (
    echo  PATH was not updated automatically.
    echo  Add this folder to the user PATH:
    echo    %TARGET%
    echo  Then open a new cmd window and type: chess
) else (
    if "%ADD_PATH%"=="1" (
        echo  Open a NEW cmd window and type:
        echo.
        echo      chess
    ) else (
        echo  PATH was not changed. Start the game with:
        echo    "%TARGET%\chess.cmd"
    )
)
echo.
echo  Start right now:
echo    "%TARGET%\chess.cmd"
echo.
echo  Uninstall:
echo    "%TARGET%\uninstall_chess.cmd"
echo.
pause
exit /b 0

:no_source
echo.
echo [chess] Game files were not found.
echo [chess] Keep install_chess.cmd next to the docs, app or chess folder.
echo.
pause
exit /b 1

:no_launcher
echo.
echo [chess] serve_chess.ps1 was not found.
echo [chess] Extract the whole ChessArena archive before installing.
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

:no_write
echo.
echo [chess] Could not create the installation folder:
echo   %TARGET%
echo [chess] Check the access rights or choose another folder:
echo   install_chess.cmd D:\Games\Chess
echo.
pause
exit /b 1

:copy_failed
echo.
echo [chess] Could not copy the game files.
echo [chess] Close the running game and try again.
echo.
pause
exit /b 1
