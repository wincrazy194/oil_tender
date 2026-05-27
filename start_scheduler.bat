@echo off
title Tender Scheduler

echo ============================================================
echo Tender Scheduler Starting...
echo ============================================================
echo.

cd /d "%~dp0"

set SCHEDULER_RUN_IMMEDIATELY=false

python scheduler.py

pause
