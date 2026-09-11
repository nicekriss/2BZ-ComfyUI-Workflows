@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-YuE2.ps1" %*
if errorlevel 1 echo Installation failed. Copy the error above when reporting a problem.
pause
