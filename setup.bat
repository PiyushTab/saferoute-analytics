@echo off
echo ======================================
echo  SafeRoute Analytics — Setup Script
echo ======================================
echo.
echo [1/4] Creating virtual environment...
python -m venv venv

echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/4] Installing dependencies...
pip install -r requirements.txt

echo [4/4] Generating dataset and training ML model...
python data_generator.py
python ml_model.py

echo.
echo ======================================
echo  Setup Complete!
echo  Run: start.bat to launch the server
echo ======================================
pause
