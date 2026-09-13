@echo off
setlocal
cd /d "%~dp0"
title Diploma Quiz Portal - Offline

if not exist ".venv\Scripts\python.exe" (
    echo Creating offline Python environment...
    where py >nul 2>&1
    if %errorlevel%==0 (
        py -m venv .venv
    ) else (
        python -m venv .venv
    )
    if errorlevel 1 (
        echo.
        echo Could not create the Python environment.
        echo Please install Python 3.10+ and try again.
        pause
        exit /b 1
    )
)

echo Installing/checking required packages...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Package installation failed.
    pause
    exit /b 1
)

echo.
echo Starting Diploma Quiz Portal for IT Lab...
echo - Server running on all network interfaces (0.0.0.0:5000)
echo - Access locally: http://127.0.0.1:5000
echo - Access from Student PCs: http://<TEACHER-PC-IP>:5000
echo   (Run "ipconfig" in Command Prompt to find your IPv4 Address)
echo.
echo Teacher login: admin / admin123
echo.
".venv\Scripts\python.exe" app.py
pause
