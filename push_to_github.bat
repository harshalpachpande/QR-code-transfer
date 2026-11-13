@echo off
set "PATH=C:\Users\Harshal\.gemini\antigravity\bin\git\cmd;%PATH%"
echo ========================================================
echo   Optical QR Code File Transfer - Push to GitHub
echo   Repository: https://github.com/harshalpachpande/QR-code-transfer
echo ========================================================
git push -u origin main
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo If GitHub asks for credentials, you can enter your Personal Access Token (PAT).
)
pause
