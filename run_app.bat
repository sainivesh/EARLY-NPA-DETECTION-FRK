@echo off
setlocal
cd /d "%~dp0"

python web_app.py
if errorlevel 1 (
    echo.
    echo NPA dashboard exited with an error.
    exit /b 1
)
