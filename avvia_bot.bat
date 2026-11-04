@echo off
rem Tiene il bot acceso su questo PC: funziona finché il PC è acceso e connesso.
cd /d "%~dp0"
python bot.py --loop --backfill 14
pause
