@echo off
cd /d "%~dp0"
py -m pip install -r requirements.txt
py LAB16I5\EXECUTAR_TUDO.py
pause
