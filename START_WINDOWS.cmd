@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 start_dashboard.py
) else (
  python start_dashboard.py
)
if errorlevel 1 (
  echo Python 3 is required to view the dashboard locally.
  pause
)
