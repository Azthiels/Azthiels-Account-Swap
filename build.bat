@echo off
REM Builds dist\Azthiels-Account-Swap.exe and then runs its self-test, so a broken exe is
REM caught here instead of when you open it.
REM
REM No --uac-admin on purpose: that flag forces a UAC prompt on every launch, which defeats
REM the scheduled-task approach (core/elevation.py) that only asks for admin once.
REM --console on purpose: it's a TUI and needs the terminal.
cd /d "%~dp0"

echo [1/3] Installing build dependencies...
python -m pip install --upgrade pyinstaller -r requirements.txt || goto :err

echo [2/3] Building exe...
python -m PyInstaller --noconfirm --clean --onefile --console ^
  --name "Azthiels-Account-Swap" ^
  --icon "%~dp0assets\img.ico" ^
  --specpath build --workpath build --distpath dist ^
  --collect-submodules azswap ^
  --collect-all textual --collect-all rich ^
  run.py || goto :err

echo [3/3] Self-test of the built exe...
dist\Azthiels-Account-Swap.exe --self-test || goto :selftest_err

echo.
echo Done: dist\Azthiels-Account-Swap.exe
pause
exit /b 0

:selftest_err
echo.
echo The exe was built but its SELF-TEST FAILED (see the [FAIL] lines above).
pause
exit /b 1

:err
echo Build failed.
pause
exit /b 1
