@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-SolAttn-MiniMax.ps1" %*
echo.
pause

