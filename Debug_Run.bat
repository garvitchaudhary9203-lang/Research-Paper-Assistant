@echo off
cd /d "%~dp0"
echo Starting Research Paper Assistant Pro in debug mode...
".venv\Scripts\python.exe" main.py
if %errorlevel% neq 0 (
    echo.
    echo Application exited with error code %errorlevel%
    pause
)
