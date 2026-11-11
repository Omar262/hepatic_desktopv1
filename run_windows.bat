@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3.11 is required to run from source.
  pause
  exit /b 1
)
if not exist .venv py -3.11 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python -m desktop.main
