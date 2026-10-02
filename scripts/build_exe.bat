@echo off
REM Build a single-file Windows executable with PyInstaller.
REM Run from the repository root:  scripts\build_exe.bat
python -m PyInstaller --noconfirm --onefile --windowed --name KhanyoITToolkit --paths src scripts\launch.py
if errorlevel 1 (
    echo Build failed.
    exit /b 1
)
echo.
echo Done: dist\KhanyoITToolkit.exe
