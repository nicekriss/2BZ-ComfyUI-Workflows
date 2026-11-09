@echo off
chcp 65001 >nul
setlocal
rem 8K 360 파노라마 PNG를 이 파일 위에 끌어다 놓으면 같은 폴더에 <이름>_360.mp4 가 생깁니다.
rem 파이썬은 컴피UI에 들어 있는 것을 먼저 찾아 씁니다(데스크톱 / 포터블). 따로 설치할 필요 없음.
set "HERE=%~dp0"
if "%~1"=="" (
  echo.
  echo  8K 파노라마 PNG 파일을 이 bat 파일 위에 끌어다 놓으세요.
  echo.
  pause
  exit /b 1
)

set "PY="
rem 0) 직접 지정: 환경변수 COMFY_PYTHON 에 python.exe 경로
if defined COMFY_PYTHON if exist "%COMFY_PYTHON%" set "PY=%COMFY_PYTHON%"

rem 1) 컴피UI 포터블: 이 폴더 또는 위쪽 폴더에 python_embeded 가 있으면
for %%D in ("%HERE%." "%HERE%.." "%HERE%..\.." "%HERE%..\..\.." "%HERE%..\..\..\..") do (
  if not defined PY if exist "%%~D\python_embeded\python.exe" set "PY=%%~D\python_embeded\python.exe"
)

rem 2) 컴피UI 데스크톱: 설정 파일에 적힌 설치 폴더의 .venv
if not defined PY (
  for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "$c=Join-Path $env:APPDATA 'ComfyUI\config.json'; if(Test-Path $c){$b=(Get-Content -Raw $c | ConvertFrom-Json).basePath; if($b){$p=Join-Path $b '.venv\Scripts\python.exe'; if(Test-Path $p){$p}}}"`) do set "PY=%%P"
)

rem 3) 컴피UI 데스크톱 기본 위치
if not defined PY if exist "%USERPROFILE%\Documents\ComfyUI\.venv\Scripts\python.exe" set "PY=%USERPROFILE%\Documents\ComfyUI\.venv\Scripts\python.exe"

rem 4) PC에 따로 깔린 파이썬(Pillow 있어야 함)
if not defined PY (
  python -c "import PIL" >nul 2>&1 && set "PY=python"
)

if not defined PY (
  echo.
  echo  [멈춤] 파이썬을 찾지 못했어요.
  echo   - 컴피UI 포터블: 이 폴더를 ComfyUI_windows_portable 폴더 안에 넣고 다시 해 보세요.
  echo   - 컴피UI 데스크톱: 컴피UI를 한 번 실행해서 설치를 끝낸 뒤 다시 해 보세요.
  echo   - 그래도 안 되면 python.exe 경로를 환경변수 COMFY_PYTHON 에 넣어 주세요.
  echo.
  pause
  exit /b 1
)

echo  파이썬: %PY%
"%PY%" -X utf8 "%HERE%make_360_video.py" "%~1"
echo.
pause
