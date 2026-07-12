@echo off
REM Run this file as Administrator (right-click -> Run as administrator).
REM It opens the Windows firewall for TCP port 8443 so phones on the same
REM WiFi can reach the voice input server. This only needs to be done once.

netsh advfirewall firewall show rule name="VoiceInput-8443" >nul 2>&1
if not errorlevel 1 (
    echo Rule "VoiceInput-8443" already exists. Nothing to do.
    goto :end
)

netsh advfirewall firewall add rule name="VoiceInput-8443" dir=in action=allow protocol=TCP localport=8443
if errorlevel 1 (
    echo FAILED to add the rule. Make sure you ran this as Administrator.
    goto :end
)
echo Rule "VoiceInput-8443" added. Phones can now reach the server on port 8443.

:end
pause
