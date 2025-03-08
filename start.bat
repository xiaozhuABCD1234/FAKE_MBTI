@echo off
echo Activating virtual environment...
call .venv\Scripts\activate.bat
echo Running Uvicorn server...
start http://127.0.0.1:8000/
uvicorn main:app --reload

pause