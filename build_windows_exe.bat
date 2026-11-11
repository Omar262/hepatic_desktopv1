@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo HEPATIC - Windows EXE Builder
echo ================================================

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python Launcher was not found.
  echo Install Python 3.11 64-bit from https://www.python.org/downloads/windows/
  echo Enable "Add python.exe to PATH" and "Python Launcher" during setup.
  pause
  exit /b 1
)

py -3.11 --version >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3.11 64-bit was not found.
  echo Install Python 3.11 64-bit, then run this file again.
  pause
  exit /b 1
)

if not exist .build-venv (
  py -3.11 -m venv .build-venv
  if errorlevel 1 goto :failed
)

call .build-venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto :failed
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :failed

pyinstaller --noconfirm --clean --windowed --onedir --name HEPATIC --collect-all PySide6 --collect-all pydicom --collect-all numpy --collect-all PIL --collect-all onnxruntime --collect-all skimage --collect-all trimesh --paths . desktop\launcher.py
if errorlevel 1 goto :failed

echo.
echo BUILD COMPLETE.
echo EXE: %CD%\dist\HEPATIC\HEPATIC.exe
echo Copy the entire dist\HEPATIC folder to another PC.
echo Python is not required on the target PC.
pause
exit /b 0

:failed
echo.
echo BUILD FAILED. Take a screenshot of this window and share it for troubleshooting.
pause
exit /b 1
