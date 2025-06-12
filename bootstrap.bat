@echo off
setlocal enabledelayedexpansion

:: ----------------------------------------------------------------------------
:: Bootstrap Script for Windows: Create and Populate a Python Virtual Environment
:: Usage: Place this file in your project root and run from Command Prompt:
::        bootstrap.bat [packages-to-install]
:: E.g.: bootstrap.bat requests flask numpy
:: ----------------------------------------------------------------------------

:: 1) Determine Python interpreter (override by setting VENV_PYTHON env var)
if defined VENV_PYTHON (
    set "PYTHON=%VENV_PYTHON%"
) else (
    set "PYTHON=python"
)

:: 2) Virtual environment directory
set "VENV_DIR=.venv"

:: 3) Remove existing virtual environment if it exists
if exist "%VENV_DIR%" (
    echo Deleting existing virtual environment "%VENV_DIR%"...
    rmdir /s /q "%VENV_DIR%"
)

:: 4) Create a new virtual environment
echo Creating virtual environment using "%PYTHON%"...
"%PYTHON%" -m venv "%VENV_DIR%"

:: 5) Activate the virtual environment
echo Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

:: 6) Upgrade pip, setuptools, and wheel
echo Upgrading pip, setuptools, and wheel...
pip install --upgrade pip setuptools wheel

:: 7) Install dependencies
:: Check if requirements.txt exists and is non-empty
set "REQ_FILE=requirements.txt"
set "REQ_SIZE=0"
for %%I in (%REQ_FILE%) do set "REQ_SIZE=%%~zI"
if exist "%REQ_FILE%" if %REQ_SIZE% gtr 0 (
    echo Installing dependencies from %REQ_FILE%...
    pip install -r %REQ_FILE%
) else if "%*" neq "" (
    echo No valid requirements.txt found, installing specified packages: %*
    pip install %*
) else (
    echo ERROR: No requirements.txt or packages specified to install.
    echo Usage: bootstrap.bat [package1 package2 ...]
    goto :EOF
)

echo.
echo ✅ Virtual environment ready in "%VENV_DIR%".
echo To activate in a new session, run:
echo    call "%VENV_DIR%\Scripts\activate.bat"
endlocal
