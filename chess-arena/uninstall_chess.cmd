@echo off
rem ============================================================
rem  CHESS ARENA - uninstall for the current Windows user
rem
rem  Removes the PATH entry and the installed game files.
rem  Your browser saves game settings and puzzle progress,
rem  so they are not deleted by this script.
rem ============================================================
setlocal EnableExtensions
chcp 65001 >nul 2>nul

if not defined LOCALAPPDATA set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"
set "TARGET=%LOCALAPPDATA%\ChessArena"

if exist "%~dp0app\chess\index.html" set "TARGET=%~dp0"
if not "%~1"=="" set "TARGET=%~1"
if "%TARGET:~-1%"=="\" set "TARGET=%TARGET:~0,-1%"

echo.
echo  CHESS ARENA - uninstall
echo  ----------------------
echo  Folder: %TARGET%
echo.

if not exist "%TARGET%" (
    echo  Nothing to remove: the folder does not exist.
    echo.
    pause
    exit /b 0
)

if exist "%TARGET%\path_tool.ps1" (
    echo  Removing the PATH entry...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%TARGET%\path_tool.ps1" remove -Dir "%TARGET%"
)

if exist "%TARGET%\app" (
    echo  Removing game files...
    rmdir /s /q "%TARGET%\app"
    if exist "%TARGET%\app" goto remove_failed
)

echo.
echo  Done. The game files and the PATH entry were removed.
echo  You can delete the remaining launcher folder manually:
echo    %TARGET%
echo.
pause
exit /b 0

:remove_failed
echo.
echo [chess] Could not remove some files.
echo [chess] Close the game server window and run this script again.
echo.
pause
exit /b 1
