@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
%PYTHON% ascii_art_studio.py
if errorlevel 1 (
 echo ASCII Art Studio could not start. See README.md for setup.
 pause
 exit /b 1
)
