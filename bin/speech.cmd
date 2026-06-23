@echo off
set "SPEECH_ROOT=%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%SPEECH_ROOT%\speech.ps1" %*
