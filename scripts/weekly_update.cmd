@echo off
rem Run by the "FL Players site update" scheduled task every morning (daily since 2026-10-13).
rem Pulls first so edits made on GitHub are not overwritten, then refreshes and pushes.
cd /d "%~dp0.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if not exist logs mkdir logs
echo ==== %date% %time% ==== >> logs\weekly_update.log
git checkout master >> logs\weekly_update.log 2>&1
rem Reset first: git pull --rebase fails outright on a dirty tree, which used to
rem stop the morning run with nothing but a line in this log. Everything local
rem here is build output and is meant to be replaced.
git reset --hard >> logs\weekly_update.log 2>&1
git pull --rebase >> logs\weekly_update.log 2>&1
if errorlevel 1 (
    echo STOP pull failed, nothing built and nothing pushed >> logs\weekly_update.log
    exit /b 1
)
python scripts\update_site.py --push >> logs\weekly_update.log 2>&1
echo exit code %errorlevel% >> logs\weekly_update.log
