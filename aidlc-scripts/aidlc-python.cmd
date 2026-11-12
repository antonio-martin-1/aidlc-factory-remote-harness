@echo off
rem Delegate to the native bootstrap; do not change the user's execution policy.
powershell.exe -NoLogo -NoProfile -File "%~dp0aidlc-python.ps1" %*
exit /b %errorlevel%
