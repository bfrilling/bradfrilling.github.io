@echo off
setlocal

REM Build a Windows downloader EXE that fetches WeeklyGrowthScanner.exe from a URL.
REM Run in Command Prompt on Windows.

python -m pip install --upgrade pip
python -m pip install pyinstaller

pyinstaller --noconfirm --clean --onefile --windowed ^
  --name WeeklyGrowthScannerDownloader ^
  windows_exe_downloader.py

echo.
echo Build complete. EXE is in dist\WeeklyGrowthScannerDownloader.exe
endlocal
