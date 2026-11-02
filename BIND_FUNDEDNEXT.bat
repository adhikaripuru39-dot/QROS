@echo off
title QROS-PROP - Bind FundedNext Account
echo ============================================================
echo   QROS-PROP: Auto-Detect & Bind Active FundedNext Account
echo ============================================================
echo.
echo Stopping running services before re-binding...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deployment\stop_services.ps1"
echo.
echo Detecting open MT5 terminal and binding FundedNext account...
"%~dp0backend\.venv\Scripts\python.exe" "%~dp0scripts\bind_active_account.py" --firm fundednext --auto-detect
echo.
echo ============================================================
echo   FundedNext Account Bound! Run START_QROS.bat to launch.
echo ============================================================
pause

