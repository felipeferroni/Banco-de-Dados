@echo off
cd /d "%~dp0"
py LAB17\EXECUTAR_TUDO.py
if errorlevel 1 pause
