@echo off
setlocal
cd /d "%~dp0"
py autoclicker.py
if errorlevel 1 pause
endlocal
