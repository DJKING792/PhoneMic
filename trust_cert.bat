@echo off
REM Run this file as Administrator (right-click -> Run as administrator).
REM It installs the local "VoiceInput Root CA" (rootCA.pem) into the Windows
REM "Trusted Root Certification Authorities" store, so browsers stop showing
REM the "Not Secure" warning for https://localhost:8443 (the desktop control
REM panel) and the LAN IP used by the phone. Only needs to be done once per
REM machine. Chrome and Edge read this store and will show a green lock;
REM Firefox keeps its own store and may still warn (use Chrome/Edge).

cd /d "%~dp0"

if not exist rootCA.pem (
    echo rootCA.pem not found.
    echo Start the server once with start.bat, then run this as Administrator.
    goto :end
)

certutil -addstore -f "Root" rootCA.pem
if errorlevel 1 (
    echo FAILED to install the certificate.
    echo Make sure you ran this file as Administrator.
    goto :end
)
echo "VoiceInput Root CA" installed as a trusted root.
echo You can now open https://localhost:8443/desktop without the warning.

:end
pause
