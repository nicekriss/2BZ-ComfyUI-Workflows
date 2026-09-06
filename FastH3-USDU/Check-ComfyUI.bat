@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Check-ComfyUI.ps1" %*
echo.
pause
