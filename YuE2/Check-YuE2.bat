@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-YuE2.ps1" -CheckOnly %*
pause
