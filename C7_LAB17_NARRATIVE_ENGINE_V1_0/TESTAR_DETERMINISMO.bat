@echo off
cd /d "%~dp0"
py TESTES\test_determinismo.py
if errorlevel 1 pause
