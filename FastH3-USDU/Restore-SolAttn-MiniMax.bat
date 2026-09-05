@echo off
setlocal
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Install-SolAttn-MiniMax.ps1" -Restore %*
echo.
pause
