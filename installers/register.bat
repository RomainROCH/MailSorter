@echo off
REM ============================================================
REM MailSorter - Windows Native Messaging Host Registration
REM ============================================================
REM Run as Administrator or from an elevated command prompt.
REM This script adds a registry key so Thunderbird/Betterbird
REM can locate the MailSorter backend via Native Messaging.
REM ============================================================

setlocal enabledelayedexpansion

REM Native Messaging application ID (must match the manifest "name")
set "APP_NAME=com.mailsorter.backend"

REM Reference manifest template (kept for compatibility/documentation)
REM The actual Windows install writes a per-user manifest in %LOCALAPPDATA%.
set "APP_MANIFEST=app_manifest.json"

REM Registry location (per-user, no admin required)
REM HKCU\Software\Mozilla\NativeMessagingHosts\%APP_NAME%
set "REG_KEY=HKCU\Software\Mozilla\NativeMessagingHosts\%APP_NAME%"

echo.
echo NOTE: On Windows, the native host should be an EXE.
echo Recommended install:
echo   powershell -ExecutionPolicy Bypass -File "%~dp0install_windows.ps1"
echo.

REM Use PowerShell registrar to generate a stable manifest pointing to the built host exe.
set PS1=%~dp0register.ps1

if not exist "%PS1%" (
    echo ERROR: Missing %PS1%
    exit /b 1
)

echo Registering Native Messaging Host (PowerShell)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"

if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Registration failed.
    echo If the host exe is missing, build it with:
    echo   powershell -ExecutionPolicy Bypass -File scripts\build_native_host_windows.ps1
    exit /b 1
)

endlocal
