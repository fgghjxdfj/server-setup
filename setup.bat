@echo off
setlocal enabledelayedexpansion
:: ============================================================
:: Server Config Generator
:: Extracts config fromvia WSL and generates server state.
:: ============================================================

set "SCRIPT_DIR=%~dp0"
set "SCRIPT=%SCRIPT_DIR%setup_server_from_client.py"
set "DEFAULT_CLIENT="
set "DEFAULT_TENTACLE=\\wsl.localhost\Ubuntu\home\wsl\Tentacle"

echo ============================================
echo  Server Setup
echo ============================================
echo.

:: Check WSL availability
where wsl.exe >nul 2>&1
if errorlevel 1 (
    echo [ERROR] wsl.exe not found. Please install WSL first.
    goto :fail
)

:: Check Python script exists
if not exist "%SCRIPT%" (
    echo [ERROR] Missing: %SCRIPT%
    goto :fail
)

:: Get client path from arg or prompt
if not "%~1"=="" (
    set "CLIENT=%~1"
) else (
    set /p "CLIENT=Client path [default: %DEFAULT_CLIENT%]: "
    if "!CLIENT!"=="" set "CLIENT=%DEFAULT_CLIENT%"
)

:: Strip surrounding quotes (handles user typing "C:\path with spaces")
for /f "delims=" %%A in (
    'powershell -NoProfile -NoLogo -Command { param($p) $p.Trim([char]0x22) } -args "!CLIENT!"'
) do set "CLIENT=%%A"

:: Get tentacle path from arg or prompt
if not "%~2"=="" (
    set "TENTACLE=%~2"
) else (
    set "TENTACLE=%DEFAULT_TENTACLE%"
)

:: Validate client directory exists
if not exist "!CLIENT!" (
    echo [ERROR] Client directory not found: !CLIENT!
    goto :fail
)

:: Output directory
set "OUTPUT=%SCRIPT_DIR%server_state"

:: Convert Windows paths to WSL paths via wslpath
for /f "usebackq delims=" %%i in (`wsl.exe wslpath -a "!CLIENT!"`) do set "WSL_CLIENT=%%i"
for /f "usebackq delims=" %%i in (`wsl.exe wslpath -a "!TENTACLE!"`) do set "WSL_TENTACLE=%%i"
for /f "usebackq delims=" %%i in (`wsl.exe wslpath -a "!OUTPUT!"`) do set "WSL_OUTPUT=%%i"
for /f "usebackq delims=" %%i in (`wsl.exe wslpath -a "!SCRIPT!"`) do set "WSL_SCRIPT=%%i"

echo Client:    !CLIENT!
echo Tentacle:  !TENTACLE! (read-only)
echo Output:    !OUTPUT!
echo.

:: Run Python script via WSL
wsl.exe python3 "!WSL_SCRIPT!" --client "!WSL_CLIENT!" --tentacle "!WSL_TENTACLE!" --output-dir "!WSL_OUTPUT!"
if errorlevel 1 (
    echo.
    echo [ERROR] Setup failed. Check log: !OUTPUT!\setup.log
    goto :fail
)

echo.
echo ============================================
echo  Done! Output: !OUTPUT!
echo  Backup: !OUTPUT!\backup\
echo  Log: !OUTPUT!\setup.log
echo ============================================
echo.
goto :end

:fail
echo.
pause
exit /b 1

:end
pause
exit /b 0
