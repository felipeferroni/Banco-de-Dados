@echo off
cd /d "%~dp0"
py TESTES\test_synthetic.py
py TESTES\test_determinism.py
pause
