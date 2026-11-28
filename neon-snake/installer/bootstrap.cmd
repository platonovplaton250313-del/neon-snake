@echo off
rem ============================================================
rem  NEON SNAKE - bootstrap installer
rem
rem  Usage:
rem      install snake
rem
rem  Downloads the installer once, installs the game and adds
rem  the commands "snake" and "install snake".
rem ============================================================
setlocal EnableExtensions
if /i not "%~1"=="snake" goto usage

set "URL=https://github.com/platonovplaton250313-del/neon-snake/releases/latest/download/NeonSnakeSetup.tar.gz"
set "WORK=%TEMP%\neon-snake-bootstrap"
set "ARCHIVE=%WORK%\setup.tar.gz"
set "EXE=%WORK%\NeonSnakeSetup.exe"
set "EXPECT_SHA=F6CE4F39B583751C89FD75D0EE252264C721A8D667E98FDDC105CDFBF0FA1002"

echo.
echo   NEON SNAKE - installing
echo.

if not exist "%WORK%" mkdir "%WORK%" >nul 2>nul
if exist "%ARCHIVE%" del /q "%ARCHIVE%" >nul 2>nul
if exist "%EXE%" del /q "%EXE%" >nul 2>nul

where curl.exe >nul 2>nul
if errorlevel 1 goto no_curl

echo   Downloading installer...
curl.exe -L -sS --fail -o "%ARCHIVE%" "%URL%"
if errorlevel 1 goto no_download
if not exist "%ARCHIVE%" goto no_download

echo   Verifying checksum...
set "GOT_SHA="
for /f "skip=1 tokens=* delims=" %%A in ('certutil -hashfile "%ARCHIVE%" SHA256') do (
    if not defined GOT_SHA set "GOT_SHA=%%A"
)
set "GOT_SHA=%GOT_SHA: =%"
if /i not "%GOT_SHA%"=="%EXPECT_SHA%" goto bad_sha

echo   Unpacking...
tar -xzf "%ARCHIVE%" -C "%WORK%"
if errorlevel 1 goto no_unpack
if not exist "%EXE%" goto no_unpack

echo   Running installer...
"%EXE%" --install
set "CODE=%errorlevel%"
if not "%CODE%"=="0" goto failed

echo.
echo   Done. Open a NEW Command Prompt window and type:
echo.
echo       snake
echo.
echo   To repair or reinstall later:  install snake
echo   To remove the game:            install snake --remove
echo.
exit /b 0

:no_curl
echo   ERROR: curl.exe was not found.
echo   Windows 10 1803 or newer is required.
exit /b 1

:no_download
echo   ERROR: could not download the installer.
echo   Check the internet connection and try again.
exit /b 1

:bad_sha
echo   ERROR: installer checksum does not match.
echo   The download may be corrupted. Please try again later.
exit /b 1

:no_unpack
echo   ERROR: could not unpack the installer.
echo   Download it manually:
echo     %URL%
exit /b 1

:failed
echo.
echo   ERROR: installation failed with code %CODE%.
exit /b %CODE%

:usage
echo.
echo   NEON SNAKE bootstrap
echo     install snake            download and install the game
echo.
exit /b 1
