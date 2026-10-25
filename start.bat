@echo off
if not exist venv\Scripts\activate.bat (
  echo Virtual environment not found. Run setup.bat first.
  pause & exit /b 1
)
call venv\Scripts\activate.bat
echo SafeRoute Analytics: http://localhost:5050  (Ctrl+C to stop)
start "" "http://localhost:5050"
python app.py
