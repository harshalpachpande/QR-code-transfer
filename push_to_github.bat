@echo off
cd /d "%~dp0"
set "PATH=C:\Users\Harshal\.gemini\antigravity\bin\git\cmd;%PATH%"
echo ========================================================
echo   Optical QR Code File Transfer - Push to GitHub
echo   Repository: https://github.com/harshalpachpande/QR-code-transfer
echo ========================================================
echo.
git push -u origin main
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   [SUCCESS] Code successfully pushed to GitHub!
    echo ========================================================
) else (
    echo.
    echo ========================================================
    echo   If GitHub authentication failed, you can sign in via
    echo   the browser prompt or use a GitHub Personal Access Token (PAT).
    echo ========================================================
)
echo.
pause
