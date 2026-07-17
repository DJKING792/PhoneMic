@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === TypMic release packer ===
python make_release.py %*
if errorlevel 1 (
  echo.
  echo [FAILED] packaging aborted.
) else (
  echo.
  echo [OK] see the dist folder for the zip.
)
pause
