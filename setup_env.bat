@echo off
REM ==========================================
REM Paper2Slides Environment Setup Script
REM ==========================================

echo [1/3] Checking Conda...
where conda >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Conda is not found in PATH. Please install Anaconda or Miniconda.
    pause
    exit /b 1
)

echo [2/3] Creating Conda environment 'paper2slides'...
call conda create -n paper2slides python=3.12 -y

echo [3/3] Installing dependencies...
REM Using 'conda run' ensures pip installs into the correct environment without global activation issues
call conda run -n paper2slides pip install -r requirements.txt

echo.
echo Setup complete! Run the following command to activate:
echo conda activate paper2slides