@echo off
echo ======================================
echo  SafeRoute Analytics - Setup
echo ======================================
where python >nul 2>nul || (echo Python was not found. Install Python 3.10+ from python.org & pause & exit /b 1)
if not exist venv (
  echo [1/3] Creating virtual environment...
  python -m venv venv || (echo Could not create venv & pause & exit /b 1)
)
call venv\Scripts\activate.bat
echo [2/3] Installing dependencies...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt || (echo Dependency install failed & pause & exit /b 1)
echo [3/3] Training the severity model...
python ml_model.py || (echo Model training failed & pause & exit /b 1)
echo.
echo Setup complete. Run start.bat to launch the app.
pause
