@echo off

REM Create venv if missing
IF NOT EXIST "venv" (
    python -m venv venv
)

REM Activate venv
call venv\Scripts\activate.bat

REM Install dependencies if missing
pip install sqlalchemy
pip install fastapi uvicorn --quiet

REM Run FastAPI app
cd ..
uvicorn main:app --reload

pause
