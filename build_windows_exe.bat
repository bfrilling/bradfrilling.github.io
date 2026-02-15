@echo off
setlocal

REM Build Windows EXE for weekly stock growth scanner desktop app.
REM Run this script in Command Prompt on Windows.

python -m pip install --upgrade pip
python -m pip install pyinstaller

pyinstaller --noconfirm --clean --onefile --windowed ^
  --name WeeklyGrowthScanner ^
  windows_stock_scanner_app.py

echo.
echo Build complete. EXE is in dist\WeeklyGrowthScanner.exe
endlocal
