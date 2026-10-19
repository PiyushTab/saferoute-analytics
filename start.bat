@echo off
echo ======================================
echo  SafeRoute Analytics — Starting Server
echo ======================================
call venv\Scripts\activate.bat
echo.
echo  Server: http://localhost:5050
echo  Press Ctrl+C to stop
echo.
start "" "http://localhost:5050"
python app.py
