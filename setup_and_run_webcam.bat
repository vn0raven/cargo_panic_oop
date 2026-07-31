@echo off
setlocal
if not exist .venv (
  py -3.12 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-webcam.txt
python main.py --webcam
pause
