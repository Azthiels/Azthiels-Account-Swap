@echo off
REM Dev run. Extra arguments are passed through, e.g.:  start.bat --doctor
cd /d "%~dp0"
python -c "import textual, cryptography" 2>nul || python -m pip install -r requirements.txt
python run.py %*
