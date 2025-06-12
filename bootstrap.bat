@echo off
setlocal

:: ----------------------------------------------------------------------------
:: Bootstrap Script for Windows: Create and Populate a Python Virtual Environment
:: Place this file in your project root and run from Command Prompt:
::    bootstrap.bat [pkg1 pkg2 …]
:: ----------------------------------------------------------------------------

:: Change to script directory to avoid path issues
pushd "%~dp0"

:: 1) Choose Python interpreter (override by setting VENV_PYTHON)
if defined VENV_PYTHON (
    set "PYTHON=%VENV_PYTHON%"
) else (
    set "PYTHON=python"
)

:: 2) Virtual environment folder
set "VENV_DIR=.venv"

:: 3) Remove any existing virtual environment
if exist "%VENV_DIR%" (
    echo Deleting existing virtual environment "%VENV_DIR%"...
    rmdir /s /q "%VENV_DIR%"
)

:: 4) Create a fresh virtual environment
echo Creating virtual environment using "%PYTHON%"...
"%PYTHON%" -m venv "%VENV_DIR%"

:: 5) Path to venv Python
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
echo Virtual environment interpreter: "%VENV_PY%"

:: 6) Upgrade installer tools
echo Upgrading pip, setuptools, and wheel...
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel >nul

:: 7) Install dependencies from requirements.txt or arguments
if exist "requirements.txt" (
    echo Installing dependencies from requirements.txt...
    "!VENV_PY!" -m pip install -r requirements.txt
) else if not "%*"=="" (
    echo Installing specified packages: %*
    "!VENV_PY!" -m pip install %*
) else (
    echo ERROR: No requirements.txt and no packages specified.
    echo Usage: bootstrap.bat [pkg1 pkg2 …]
    popd
    endlocal
    exit /b 1
)

:: 8) Show installed packages for verification
echo.
echo Installed packages in %VENV_DIR%:
"!VENV_PY!" -m pip list

:: Return to original directory
popd

echo.
echo ✅ Virtual environment ready in "%VENV_DIR%".
echo To activate, run:
echo    %VENV_DIR%\Scripts\activate.bat
endlocal
