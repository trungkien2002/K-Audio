@echo off
title K-Audio
cd /d "%~dp0"

echo ============================================
echo   K-Audio
echo   All-in-One Story-to-Video Pipeline
echo ============================================
echo.

:: Check Python
set PYTHON_CMD=python
python --version >nul 2>&1
if errorlevel 1 (
    py -3.11 --version >nul 2>&1
    if errorlevel 1 (
        echo [!] Khong tim thay Python.
        echo     Hay cai dat Python tu python.org
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=py -3.11
    )
)
echo [OK] %PYTHON_CMD%

:: Install PySide6 if needed
echo.
echo [1/3] Kiem tra PySide6...
%PYTHON_CMD% -c "import PySide6" 2>nul
if errorlevel 1 (
    echo       Dang cai PySide6...
    %PYTHON_CMD% -m pip install PySide6 -q
    if errorlevel 1 (
        echo [!] Loi: Khong the cai PySide6
        pause
        exit /b 1
    )
    echo       Da cai PySide6.
) else (
    echo       PySide6 OK.
)

:: Install core deps
echo.
echo [2/3] Kiem tra thu vien phu tro...
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo [!] Canh bao: Mot so thu vien co the chua duoc cai dat.
) else (
    echo       Thu vien OK.
)

:: Create directories if needed
echo.
echo [3/3] Kiem tra cau truc thu muc...
if not exist "config" mkdir config
if not exist "assets\fonts" mkdir assets\fonts
if not exist "assets\intro" mkdir assets\intro
if not exist "assets\outro" mkdir assets\outro
if not exist "assets\overlays" mkdir assets\overlays
if not exist "assets\icons" mkdir assets\icons
if not exist "data" mkdir data
echo       OK.

:: Launch app
echo.
echo Khoi dong K-Audio...
echo.
%PYTHON_CMD% main.py

echo.
echo Ung dung da ket thuc.
pause
