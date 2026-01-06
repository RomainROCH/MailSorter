@echo off
REM ============================================================
REM MailSorter - Windows Native Messaging Host Registration
REM ============================================================
REM Run as Administrator or from an elevated command prompt.
REM This script adds a registry key so Thunderbird/Betterbird
REM can locate the MailSorter backend via Native Messaging.
REM ============================================================

setlocal enabledelayedexpansion

REM --- Configuration ---
set APP_NAME=com.mailsorter.backend
set MANIFEST_FILE=%~dp0..\backend\app_manifest.json

REM Resolve absolute path of manifest file
for %%I in ("%MANIFEST_FILE%") do set MANIFEST_ABS=%%~fI

REM Verify manifest exists
if not exist "%MANIFEST_ABS%" (
    echo ERROR: Manifest file not found at %MANIFEST_ABS%
    echo Please ensure backend/app_manifest.json exists.
    exit /b 1
)

REM --- Registry key path (per-user, no admin required) ---
set REG_KEY=HKCU\Software\Mozilla\NativeMessagingHosts\%APP_NAME%

echo Registering Native Messaging Host...
echo   App Name   : %APP_NAME%
echo   Manifest   : %MANIFEST_ABS%
echo   Registry   : %REG_KEY%

reg add "%REG_KEY%" /ve /t REG_SZ /d "%MANIFEST_ABS%" /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo SUCCESS: Native Messaging Host registered.
    echo Restart Thunderbird/Betterbird to apply changes.
) else (
    echo.
    echo ERROR: Failed to add registry key. Try running as Administrator.
    exit /b 1
)

endlocal
