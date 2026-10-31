@echo off
title QROS-PROP S-Tier VPS Setup
echo ============================================================
echo   QROS-PROP 1-Click Automated VPS Setup & Installation
echo ============================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deployment\deploy_vps.ps1"
echo.
pause

