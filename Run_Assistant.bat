@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Error: Virtual environment (.venv) not found in "%CD%"
    echo Please make sure this file is placed inside the "Research Paper Assistant" folder.
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" main.py
