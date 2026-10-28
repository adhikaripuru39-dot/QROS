@echo off
title Start QROS-PROP Services
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deployment\start_services.ps1"
pause
