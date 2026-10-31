@echo off
title Stop QROS-PROP Services
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deployment\stop_services.ps1"
pause

