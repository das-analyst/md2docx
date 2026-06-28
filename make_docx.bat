@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
    echo Creating virtual environment and installing dependencies...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

if "%~1"=="" (
    echo Usage: make_docx.bat path\to\spec.spec.md [-o output_dir] [other documents.py flags]
    echo.
    echo Example:
    echo   make_docx.bat C:\cli-projects\mba_ai\courses\mgt500\MGT500.spec.md -o C:\cli-projects\mba_ai\courses\mgt500
    exit /b 1
)

python documents.py %*
